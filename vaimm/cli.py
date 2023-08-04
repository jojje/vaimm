#!/usr/bin/env python
import argparse
import os
import platform
import sys

from textwrap import fill, indent
from typing import Iterable

from .net import download_model_files
from .vai import find_backend_files, find_models_metadata, parse_models_metadata
from .version import __version__

WINDOWS_DEFAULT_JSON_DIR = "C:\\ProgramData\\Topaz Labs LLC\\Topaz Video AI\\models"
ENV_JSON_DIR = 'TVAI_MODEL_DIR'
ENV_MODEL_DIR = 'TVAI_MODEL_DATA_DIR'
ENV_BACKEND = 'TVAI_BACKEND'
ENV_COOKIE = 'TVAI_COOKIE'
AVG_MODEL_SIZE_MB = 91

def main():
    opts = parser_args()
    metas = find_models_metadata(opts.json_dir)
    if opts.cmd == 'list-backends':
        list_backends(metas)
    elif opts.cmd == 'list-models':
        list_models(metas, opts.backend)
    elif opts.cmd == 'list-files':
        list_backend_files(metas, opts.backend, opts.include)
    elif opts.cmd == 'download':
        download_missing_files(metas, opts.backend, opts.include, opts.dir, opts.threads, opts.cookie)
    else:
        print(f'command {opts.cmd} not implemented (this is a bug)', file=sys.stderr)
        sys.exit(-1)


def parser_args() -> argparse.Namespace:
    json_dir = find_models_json_dir()
    model_dir = os.getenv(ENV_MODEL_DIR)
    backend = os.getenv(ENV_BACKEND)
    cookie = os.getenv(ENV_COOKIE)

    helper = argparse.ArgumentDefaultsHelpFormatter

    parser = argparse.ArgumentParser(
        formatter_class=helper,
        description=f'VAI Models Manager (v{__version__}): Download missing models for TopazLabs Video AI'
    )
    parser.add_argument('--json-dir', metavar='path', default=json_dir, required=not json_dir,
                        help='Directory where the VAI model json files reside. E.g. alq-13.json. Defaults to the '
                             f'value of the environment variable {ENV_JSON_DIR} if set, else checks if any of the '
                              'default folders exist, otherwise you just have to specify it yourself.')

    commands = parser.add_subparsers(dest='cmd', title='commands', metavar='')
    commands.add_parser('list-backends', help='Lists the available backends that VAI supports')

    mlist = commands.add_parser('list-models', help='Lists available models for a given backend')
    mlist.add_argument('--backend', metavar='name', default=backend, required=not backend,
                       help=f'Name of the backend to list models for (env: {ENV_BACKEND})')

    files = commands.add_parser('list-files', help='Lists model files for a backend')
    files.add_argument('--backend', metavar='name', default=backend, required=not backend,
                       help=f'Name of the backend to list the model files for (env: {ENV_BACKEND})')
    files.add_argument('--include', metavar='ids', help='Commma separated list of specific model(s) to include')

    download = commands.add_parser('download', formatter_class=helper,
                                   help='Download VAI models missing from your model data directory')
    download.add_argument('--backend', metavar='name', default=backend, required=not backend,
                          help=f'Name of the backend to fetch models for (env: {ENV_BACKEND})')
    download.add_argument('--include', metavar='ids', help='Commma separated list of specific model(s) to include')
    download.add_argument('-d', '--dir', metavar='path', default=model_dir, required=not model_dir,
                          help=f'Path to your model data directory (env: {ENV_MODEL_DIR}).')
    download.add_argument('-c', '--cookie', metavar='str', default=cookie, required=not cookie,
                          help='The value of the cf_clearance cookie, required to download files from topaz '
                               'Cloudflare CDN. You can find this when logged into the topaz website, by opening '
                               '"developer tools" in firefox (or inspector in chrome), then the network tab. Once '
                               'that is done, download a test model from the browser. E.g: '
                               'https://veai-models.topazlabs.com/prap-v3-fp32-ov.tz . Finally look at the request '
                               'headers for the associated request, and the Cookie header. That header has the value '
                               'required. It looks like "cf_clearance: <the-string-you-need-here>" '
                               f'(env: {ENV_COOKIE}).')
    download.add_argument('-t', '--threads', metavar='n', default=4, type=int,
                          help='Number of concurrent downloads to use')

    if len(sys.argv) < 2:
        sys.argv.append('-h')
    return parser.parse_args()


def list_backends(model_dicts:Iterable[dict]):
    backends = sorted(set(b for m in model_dicts for b in m['backends']))
    print('Supported backends:', ', '.join(backends))


def list_models(model_dicts:Iterable[dict], backend:str):
    parsed = parse_models_metadata(model_dicts, backend)
    models = sorted(parsed, key=lambda m: m.id + str(m.version))

    print('Available models:')
    for m in models:
        id = f"{m.id}-{m.version}"
        desc = indent(fill(m.desc, 78), prefix=" "*11)
        print(f"\n* {id:<8s} {m.name}\n{desc}")


def list_backend_files(model_dicts:Iterable[dict], backend:str, includes:str):
    files = sorted(find_backend_files(model_dicts, backend, includes))
    print('Model files:\n', file=sys.stderr)
    print('\n'.join(files))
    print(f'\nEstimated total size: {len(files) * AVG_MODEL_SIZE_MB/(1<<10):.2f} GiB', file=sys.stderr)


def download_missing_files(model_dicts:Iterable[dict], backend:str, includes:str,
                           data_dir:str, threads:int, cookie:str):
    missing_files = find_missing_files(model_dicts, backend, includes, data_dir)
    download_model_files(missing_files, threads, cookie)


def find_missing_files(model_dicts:Iterable[dict], backend:str, includes:str, data_dir:str):
    backend_files = find_backend_files(model_dicts, backend, includes)
    target_files = (os.path.join(data_dir, file) for file in backend_files)
    missing_files = (file for file in target_files if not os.path.exists(file))
    return missing_files


def find_models_json_dir() -> str:
    candidates = [
        os.getenv('ENV_JSON_DIR', ''),
        os.path.join(os.getenv('PROGRAMDATA', ''), 'Topaz Labs LLC\\Topaz Video AI\\models'),
        '/Applications/Topaz Video AI.app/Contents/Resources/models',
        '/opt/TopazVideoAIBETA/models',
    ]
    for path in candidates:
        if path and os.path.exists(f'{path}/alq-13.json'):
            return path
