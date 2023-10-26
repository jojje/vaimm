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
        failed = []

        try:
            with tqdm(total=len(futures), unit=' files ', desc='Downloading', leave=True) as pbar:
                for future in as_completed(futures):
                    file = futures[future]
                    exc = future.exception()

                    if exc:
                        failed.append((file, exc))
                    else:
                        total_bytes_downloaded += future.result()

                    elapsed = time.time() - started_at
                    bps = total_bytes_downloaded / elapsed
                    speed = f'{scale_unit(bps)}/s'
                    pbar.update(1)
                    pbar.set_postfix({'speed': speed, 'failed': len(failed)})

        except KeyboardInterrupt:
            for future in futures:
                future.cancel()
            executor.shutdown(wait=False)
            raise

    if failed and len(failed) <= len(futures):
        print(f'Download completed, {len(failed)} out of {len(futures)} files failed to download.')
        print('\nThe failed downloads:')
        for file, error in failed:
            print(f'  {os.path.basename(file)}  (failure reason: {error})')
    else:
        print(f'Download completed successfully with {scale_unit(total_bytes_downloaded)} of data fetched.')


def retry(max_tries=4, initial_wait_secs=4, backoff=4):
    retriable_codes = {408, 423, 429, 500, 502, 503, 504, 507, 599}

    def find_retry_after_seconds(headers:dict):
        s = headers.get('Retry-After')
        if not s:
            return None
        if s.isdigit():
            return int(s)

        # in date format: <day-name>, <day> <month> <year> <hour>:<minute>:<second> GMT
        t = time.strptime(s, '%a, %d %b %Y %H:%M:%S %Z')
        delta_secs = time.mktime(t) - time.mktime(time.gmtime())
        return delta_secs

    def handle_http_error(exc:HTTPError) -> bool:
        if exc.code in retriable_codes:
            delay_secs = find_retry_after_seconds(dict(exc.headers))
            if delay_secs:
                print(f'Intermittent error: {exc}, Retrying in {delay_secs} seconds '
                      'as per server ask...')
                time.sleep(delay_secs)
                return True  # already delayed, so let caller know not to delay further
            return False     # no specific delay asked from server; apply standard retry logic
        else:
            raise exc  # terminal fault, not a retriable http error

    def decorator(func):
        @wraps(func)
        def inner(*args, **kw):
            wait_duration = initial_wait_secs
            for attempt in range(max_tries):
                try:
                    return func(*args, **kw)

                except (HTTPError, ContentTooShortError) as exc:
                    if attempt == max_tries - 1:
                        raise exc  # too many retries

                    if isinstance(exc, HTTPError):
                        delayed = handle_http_error(exc)
                        if delayed:
                            continue

                    print(f'Error encountered during download: {exc}, Retrying in {wait_duration} seconds...',
                          file=sys.stderr)
                    time.sleep(wait_duration)
                    wait_duration *= backoff
        return inner
    return decorator


@retry()
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

    # ensure output (download) directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # ensure user doesn't end up with broken models in case something goes wrong / program is aborted mid-stride
    os.rename(tempfile, filename)
    return bytes_written
