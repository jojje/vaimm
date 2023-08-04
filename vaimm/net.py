import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from typing import Iterable
from urllib.request import Request, urlopen, ContentTooShortError, HTTPError

from tqdm import tqdm

from .version import __version__

DOWNLOAD_URL_PREFIX = 'https://veai-models.topazlabs.com/'

def download_model_files(missing_files:Iterable[str], threads:int, cookie:str):
    def assert_download_success(future) -> int:  # bytes written
        try:
            return future.result()  # Just check that no error was generated during the download
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            print(f'Download failed: {e}', file=sys.stderr)
            sys.exit(1)

    def scale_unit(nbytes:int) -> str:
        if nbytes > 1<<30:
            return f'{nbytes/(1<<30):.2f} GiB'
        if nbytes > 1<<20:
            return f'{nbytes/(1<<20):.2f} MiB'
        if nbytes > 1<<10:
            return f'{nbytes/(1<<10):.2f} KiB'
        return f'{nbytes} B'

    download_jobs = ((DOWNLOAD_URL_PREFIX + os.path.basename(file), file) for file in missing_files)

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(download_file, url, cookie, file): file for url, file in download_jobs}
        if not futures:
            print('No missing model files to download')
            return

        started_at = time.time() - 0.00001
        total_bytes_downloaded = 0
        elapsed = 0

        try:
            with tqdm(total=len(futures), unit=' files ', desc='Downloading', leave=True) as pbar:
                for future in as_completed(futures):
                    total_bytes_downloaded += assert_download_success(future)
                    elapsed = time.time() - started_at
                    bps = total_bytes_downloaded / elapsed
                    speed = f'{scale_unit(bps)}/s'
                    pbar.update(1)
                    pbar.set_postfix({'speed': speed})

        except KeyboardInterrupt:
            for future in futures:
                future.cancel()
            executor.shutdown(wait=False)
            raise

    print(f'Download completed successfully with {scale_unit(total_bytes_downloaded)} of data fetched.')


def retry(max_tries=5, initial_wait_secs=1, backoff=3):
    def decorator(func):
        @wraps(func)
        def inner(*args, **kw):
            wait_duration = initial_wait_secs
            for attempt in range(max_tries):
                try:
                    return func(*args, **kw)
                except (HTTPError, ContentTooShortError) as exc:
                    if isinstance(exc, HTTPError) and 400 <= exc.code < 500 and exc.code not in (408,429):
                        raise  # don't retry on file not found, or invalid cf-cookie
                    if attempt == max_tries - 1:
                        raise
                    print(f'Error encountered during download: {exc}, Retrying in {wait_duration} seconds...',
                          file=sys.stderr)
                    time.sleep(wait_duration)
                    wait_duration *= backoff
        return inner
    return decorator


@retry(max_tries=5)
def download_file(url:str, cookie:str, filename:str, chunk_size:int=8<<10) -> int:
    request = Request(url, headers={
        'cookie': f'cf_clearance={cookie}',
        'accept': '*/*',
        'user-agent': f'vaimm/{__version__}',  # for some reason cloudflare rejects python's UA !?
        'accept-encoding': '*',
    })

    tempfile = f'{filename}.incomplete'
    bytes_written = 0

    with urlopen(request) as response:
        expected_bytes = response.headers.get('content-length')
        with open(tempfile, 'wb') as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:  # end of data in stream
                    break
                f.write(chunk)
                bytes_written += len(chunk)

    if expected_bytes is not None:
        expected_bytes = int(expected_bytes)
        if expected_bytes != bytes_written:
            raise ContentTooShortError(
                f'Incomplete data from server - expected: {expected_bytes}, got: {bytes_written} for url: {url}', None)

    # ensure user doesn't end up with broken models in case something goes wrong / program is aborted mid-stride
    os.rename(tempfile, filename)
    return bytes_written
