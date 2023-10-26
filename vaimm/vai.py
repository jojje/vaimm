# domain logic for interpreting the VAI json file data structures
import json
from dataclasses import dataclass
from glob import glob
from typing import Iterable, List
from .tensorrt import TRT


@dataclass
class Model:
    id: str
    name: str
    desc: str
    version: str
    files: List[str]


def parse_models_metadata(model_metas:Iterable[dict], backend:str, trt:TRT) -> Iterable[Model]:
    def permute(blocks):
        # assumption: the blocks data structure represents inlined tuples of (height, width)
        # this means that combination 1 is (block[0], block[1]), 2 is (block[2], block[3]) and so on.
        # same scheme applies to the 'capabilities' arrays for tensor-rt
        return ((h, w) for h,w in zip(blocks[::2], blocks[1::2]))

    def derive_filename(model_id, version, net, scale, width, height):
        # e.g. fgnet-fp32-[H]x[W]-[S]x-ox.tz
        suffix = (net
                  .replace('[H]', str(height))
                  .replace('[W]', str(width))
                  .replace('[S]', str(scale)))
        if trt:
            suffix = (suffix
                      .replace('[R]', str(trt.os_family))
                      .replace('[C]', str(trt.gpu_family)))
        return f'{model_id}-v{version}-{suffix}'

    def find_model_files_for_backend(model, backend):
        backend_dict = model['backends'].get(backend, {})
        capabilities = backend_dict.get('capabilities', [])
        model_id = model['shortName']
        version = model['version']

        scales = backend_dict.get('scales', {})
        for scale in scales:
            for net in scales[scale].get('nets', {}):
                blocks = scales[scale].get('blocks', {})
                if blocks:
                    if capabilities:
                        compatible = trt and trt.gpu_family in capabilities
                        if not compatible:
                            continue
                    block_combinations = permute(blocks)
                    for width, height in block_combinations:
                        filename = derive_filename(model_id, version, net, scale, width, height)
                        yield filename

    def parse(model):
        id = model['shortName']
        desc = model.get('gui', {}).get('desc', '<no description provided by topaz>')
        files = list(find_model_files_for_backend(model, backend))
        version = model['version']

        name = model.get('gui', {}).get('name')
        if not name:
            name = model.get('displayName')
        if not name:
            name = id

        return Model(id, name, desc, version, files)

    for meta in model_metas:
        model = parse(meta)
        if model.files:
            yield model


def find_models_metadata(json_dir:str) -> dict:
    def read():
        path = json_dir.replace('\\', '/')  # glob doesn't understand windows paths

        for fn in glob(f'{path}/*.json'):
            with open(fn, 'rb') as f:
                yield json.load(f)

    for d in read():
        if 'backends' in d:
            yield d


def find_backend_files(model_dicts:Iterable[dict], backend:str, includes:str, trt:TRT) -> Iterable[str]:
    want = set([s.strip() for s in includes.split(',') if s.strip()]) if includes else set()
    parsed = parse_models_metadata(model_dicts, backend, trt)
    models = (model for model in parsed
              if (not want) or (f'{model.id}-{model.version}' in want))
    files = (file for model in models for file in model.files)
    return files
