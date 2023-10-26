
# vaimm

VAI model manager

Quickly download models for Topaz Video AI.

## Installation

```bash
pip install vaimm
```

## Usage

```text
usage: vaimm [-h] [--json-dir path]  ...

VAI Models Manager (<version>): Download missing models for TopazLabs Video AI

options:
  -h, --help       show this help message and exit
  --json-dir path  Directory where the VAI model json files reside. E.g.
                   alq-13.json. Defaults to the value of the environment variable
                   TVAI_MODEL_DIR if set, else checks if any of the default folders
                   exist, otherwise you just have to specify it yourself. (default:
                   C:\ProgramData\Topaz Labs LLC\Topaz Video AI\models)

commands:
    list-backends  Lists the available backends that VAI supports
    list-models    Lists available models for a given backend
    list-files     Lists model files for a backend
    download       Download VAI models missing from your model data directory
```

Each command takes options and arguments. List which ones are available,
optional and required by providing `--help` after the command name. 

Example: `vaimm list-backends --help`

To use any of the commands, you have to specify where the VAI model JSON files
are. The program will check the default locations for windows, macos and linux,
and show what it deduced to be the location dynamically in the help message If
you're not using a standard location, you'll be required to specify the location
yourself.

Example: `vaimm --json-dir /opt/TopazVideoAIBETA/models list-backends`

The list commands are there to give you some information about the models and
versions available, and what model files are required for each. If you are only
interested in a subset of the models, you can tell the program to filter only on
those.

For example, to only show the latest version of the model files for Artemis Medium and
Prometheus, applicable to the ONNX (32-bit) backend:

```
$ vaimm list-files --backend onnx --include prob-3,amq-13

amq-v13-fgnet-fp32-256x352-1x-ox.tz
amq-v13-fgnet-fp32-256x352-2x-ox.tz
...
prob-v3-fgnet-fp32-576x672-2x-ox.tz
prob-v3-fgnet-fp32-576x672-4x-ox.tz

Estimated total size: 4.80 GiB
```

_Tip: You can use the list-files command to previous what will be downloaded,
since it's the exact same set of files that will be when using the `download`
command with the same `include` filter and `backend`._

In order to download the right models for your particular machine, you have to
know which VAI backend you are using, and tell the program to use models for
that specific backend.

the available backends as of this writing are:

```
$ vaimm.py backends
Supported backends: coreml, onnx, onnx16, openvino, openvino16, openvino8, tensorrt-off
```

## Downloading models

Just like the list-files command, the `download` command also allows you to select a
subset of models to download. You _really_ want to do this, since the complete
set of models are hundred(s) of gigabyte in size.

Let's say you want to download the same two model files ("onnx networks") listed
above, for a RTX 3080 card which uses 16-bit floating point.

```
$ vaimm download --backend onnx16 --include prob-3,amq-13 --dir . --cookie "$COOKIE"

Downloading: 100%|████████████████| 54/54 [00:26<00:00,  2.07 files /s, speed=64.04 MiB/s]
Download completed successfully with 1.63 GiB of data fetched.
```

To instead download _TensorRT_ optimized variants for a RTX 30xx series card:

```
$ vaimm download --backend tensorrt --gpu RTX30 --include prob-3,amq-13 --dir . --cookie "$COOKIE"

Downloading: 100%|████████████████| 54/54 [00:26<00:00,  2.07 files /s, speed=64.04 MiB/s]
Download completed successfully with 1.63 GiB of data fetched.
```

* `--dir` is the directory the files should be saved to. You'd likely want to
  specify the `TVAI_MODEL_DATA_DIR` directory. I.e. where you already have some
  model files that VAI downloaded on-the-fly as you used that program.
* `--cookie` is a cloudflare authentication string which Topaz has configured
  their CDN to require. This value is likely unique per user, so you have to
  discover what yours is before you can download any models. How to find this
  value is in the help description for the command. See below.

```
usage: vaimm download [options]

options:
  -h, --help            show this help message and exit
  --backend name        Name of the backend to fetch models for (env: TVAI_BACKEND)
                        (default: None)
  --include ids         Commma separated list of specific model(s) to include
                        (default: None)
  --gpu family          Name of the nVidia GPU family for TensorRT model fetching. 
                        One of: RTX20, RTX30, RTX40. (env: TVAI_GPU_FAMILY)
                        (default: None)
  -d path, --dir path   Path to your model data directory (env:
                        TVAI_MODEL_DATA_DIR). (default: None)
  -c str, --cookie str  The value of the cf_clearance cookie, required to download
                        files from topaz Cloudflare CDN. You can find this when
                        logged into the topaz website, by opening "developer tools"
                        in firefox (or inspector in chrome), then the network tab.
                        Once that is done, download a test model from the browser.
                        E.g: https://veai-models.topazlabs.com/prap-v3-fp32-ov.tz .
                        Finally look at the request headers for the associated
                        request, and the Cookie header. That header has the value
                        required. It looks like "cf_clearance: <the-string-you-need-
                        here>" (env: TVAI_COOKIE). (default: None)
  -t n, --threads n     Number of concurrent downloads to use (default: 1)
```

Option details worth clarifying:

* The `--include` option. It says default is None. What that _really_
means is that there is no filtering for specific model IDs done by default. So
_all_ models for the backend will be downloaded if you don't limit the scope to
just a few chosen, as was been done in the examples up until now.
* `--gpu` option. This is only relevant if you want to download TensorRT optimized models. On Windows auto-detection of your GPU will be attempted, so the correct card family may already be filled in. Otherwise you have to explicitly specify for which RTX graphics card family you want to download TensorRT models for.

## TensorRT

TopazLabs provides a set of TensorRT models to speed up inference (video processing), but only for a subset of video cards and platforms.

Specifically, only nVidia cards are supported, and of those cards, only the RTX 20, 30 and 40 series/families of cards. Further more, TensorRT models are only provided for Windows and Linux operating systems.

When listing or downloading TensorRT models, the script will only show or download models that are available for your specified graphics card family, **and** that are available for the operating system you run the script on. 

On Windows, attempts are made to auto-detect the right configuration. On Linux, or if you want to download TensorRT models for a specific RTX card family that isn't installed on the machine, you then need to specify the card family using the `--gpu` option.

The card family that has been auto-detected is shown as `default: <family>` in the download and list-models command help text, so you can see there what type of TensorRT models will be downloaded or listed.

Finally, to make things simple. The `--gpu` option only matters if you specify the `tensorrt` backend for model listing or downloading. It has no bearing on any other backends.

## Environment variables

To reduce the amount of typing, and to make it easier to create scripts that run
on different machines with different backends, directory locations etc, most of
the command options have environment variable alternatives. 

When an environment variable for an option has been set, it becomes the default
value for the option on all commands that would normally require the option to
be specified.

The usage help lists which environment variable provides default for which
option, but here is a digest:

* `TVAI_MODEL_DIR`: the global `--json_dir` option.
* `TVAI_MODEL_DATA_DIR`: the download `--dir` option.
* `TVAI_COOKIE`: the download `--cookie` option.
* `TVAI_BACKEND`: the `--backend` option used by several commands.
* `TVAI_GPU_FAMILY`: the `--gpu` option used by several commands.

## FAQ

### Q: What happens if there is a network problem during the download?

If there is a non-fatal error, the file that encountered the download failure
will be retried automatically. Each individual file transfer will be retried up
to five times, using an exponential backoff. That is, every time a file
encounters a non-terminal failure it will wait longer and longer to retry that
file (attempts^3 to be exact). The reason for this is to give cloudflare time to
rectify intermittent problems without us constantly hammering on some poor CDN
node that has issues. After four failures, the final wait time will be about 1
minute and a half. If the error still persists, the program will abort. 

For terminal faults, such as you providing the wrong cloudflare cookie, the
program aborts immediately (fail fast).

### Q: Can I abort and resume downloads?

Yes. The program will automatically deduce which model files are missing from
the specified target directory, and _only_ download those that are missing.

Resuming works by re-downloading any missing model files that were not
completely and successfully downloaded.

### Q: How can I be sure the model files don't get corrupted if my machine crashes or I terminate the program mid-stride?

Files in-flight (being downloaded) are written to a temporary file in the
directory you specified with the `--dir` option. They have the suffix
`.incomplete` appended to them. Once a file has been fully downloaded, and its
size matches that which the CDN server announced should be the expected size,
the temporary file is renamed to the actual model filename. I.e. the download
suffix is stripped.

Now barring any mechanical issues with your drive, computer or operating system
bugs, it should be safe to assume that the models downloaded are not corrupted.

Unfortunately the Cloudflare CDN doesn't provide us a message digest (e.g.
sha/md sum) that we could use to compute the file integrity. As such we just
have to trust that what the CDN sent over the wire, and what this program
instructed the operating system to store, has actually been stored.

### Q: The size estimate for the model files is way-off, why?

The estimate uses an average of 91 MiB per model file. That was the average file
size I had on my windows machine with ~300-400 fp32 model files in total. As
simple as that.

If you are using a 16-bit model backend, the size would likely be half of the
estimate.

Do note, since Topaz doesn't publish the total model sizes, or provide that
information as part of the VAI program or an API, this was the only option to
get an indication of model sizes without downloading all files for all backends.

### Q: I work for TopazLabs and I really don't like this program. How can I block it?

The UA used by the program is `vaimm/<version>`. Just block that.

However, I'd encourage you to have a conversation with the user community on
your forum before you do, since as you know, people have been clamoring for a
quick way to download models for a very long time. Just killing _a solution_ to
the problem without providing a comparable alternative would "not be good form".

## Development

To execute the main function of the program from the project's root directory:
```
python -m vaimm
```

To simplify development, common actions are provided via [Makefile](Makefile) targets:

* `test` - default targets, runs pytest on the project
* `lint` - runs flake8 lint check
* `dist` - create a wheel package distribution, ready to be uploaded to pypi or given to someone else.
* `clean` - removes temporary files generated as part of the package creation.

## Contribution

Pull requests are extremely welcome. But defining the problem comes first. So
start with an Issue ticket.

I likely won't maintain this actively once I've downloaded the models that _I_
need, so keeping track of if TopazLabs breaks this program through changes on
their backend or the json model files format provided by the VAI application
will be a joint user responsibility.

if TopazLabs changes anything that should be catered for, please open an
issue so we can discuss that first. Then once the problem has been defined, open
a PR with a fix :)
