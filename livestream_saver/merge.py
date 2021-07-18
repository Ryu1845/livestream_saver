#!/bin/env python3
from os import sep, remove, path, stat, rename
import subprocess
from json import load
from pathlib import Path
from shutil import copyfileobj
import logging
from imghdr import what

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


def get_metadata_info(path):
    try:
        with open(path + sep + "metadata.json", 'r') as fp:
            return load(fp)
    except Exception as e:
        logger.exception(f"Exception while trying to load metadata.json: {e}")
        return {}


def concat(datatype, video_id, seg_list, output_dir, method=0):
    """
    Concatenate segments.
    :param str datatype:
        The type of data. "video" or "audio"
    :param str video_id:
        Youtube ID.
    :param list seg_list:
        List of path to .ts files.
    :param str output_dir:
        Output directory where to write resulting file.
    :rtype: str
    :returns:
        Path to concatenated video or audio file.
    """
    METHOD = ["concat", "concat_demuxer"]

    logger.info(f"Trying concatenation method: \"{METHOD[method]}\".")

    concat_filename = f"concat_{video_id}_{datatype}.ts"
    concat_filepath = output_dir + sep + concat_filename

    # Determine container type according to codec
    if datatype == "vp9":
        ext = "webm"
    elif datatype == "aac":
        ext = "m4a"
    elif datatype == "h264":
        ext = "mp4"
    else:
        ext = "m4a" if datatype == "audio" else "mp4"

    ffmpeg_output_filename = f"{output_dir}{sep}\
{video_id}_{datatype}_{METHOD[method]}_ffmpeg.{ext}"

    if path.exists(ffmpeg_output_filename):
        logger.info(
            f"Skipping concatenation because \"{ffmpeg_output_filename}\" "
            "already exists from a previous run."
        )
        return ffmpeg_output_filename

    list_file_path = None

    if METHOD[method] == "concat_demuxer":
        # http://ffmpeg.org/ffmpeg-formats.html#concat-1
        # Does not work, duration is always messed up.
        # Also a bunch of "Auto-inserting h264_mp4toannexb bitstream filter"
        # warnings (-auto_convert 0 might disable them, but no different result)
        list_file_path = f"{output_dir}{sep}list_{video_id}_{datatype}.txt"
        with open(list_file_path, "w") as f:
            for i in seg_list:
                f.write(f"file '{i}'\n")

        cmd = ["ffmpeg", "-hide_banner", "-y",
               "-f", "concat",
               "-safe", "0",
               "-i", list_file_path,
               "-map_metadata", "-1", # remove metadata
            #  "-auto_convert", "0" # might disable warnings?
               "-c", "copy",
            #    "-bsf:v", "h264_mp4toannexb", # or [hevc|h264]_mp4toannexb
               ffmpeg_output_filename]

    elif METHOD[method] == "concat_protocol":
        # http://www.ffmpeg.org/faq.html#How-can-I-concatenate-video-files_003f
        # This seems to be identical to our default method, except ffmpeg does
        # everything for us and doesn't require a temporary concat file.
        # Some people say it doesn't work with MP4 files. Also, there is a point
        # where the argument length is too long, so this can overflow. Stupid!
        list_files = "|".join([str(f.name) for f in seg_list])

        cmd = ["ffmpeg", "-hide_banner", "-y",
              f"concat:\"{list_files}\"", # this may overflow. Stupid design!
               "-map_metadata", "-1",  # remove metadata
               "-c", "copy",
               ffmpeg_output_filename]
        print(f"len cmd: {len(cmd)} cmd:\n{cmd}")

    else:
        if not path.exists(concat_filepath):
            # Concatenate segments through python
            with open(concat_filepath,"wb") as f:
                for i in seg_list:
                    with open(i, "rb") as ff:
                        copyfileobj(ff, f)
        # Fix broken container. This seems to fix the messed up duration.
        # Note: '-c:a' if datatype == 'audio' else '-c:v' but '-c copy' might work for both here.
        cmd = ["ffmpeg", "-hide_banner", "-y",
               "-i", concat_filepath,
               "-map_metadata", "-1", # remove metadata
               "-c", "copy",
               ffmpeg_output_filename]

    cproc = None
    try:
        cproc = subprocess.run(cmd,
                               check=True,
                               capture_output=True,
                               text=True)
        logger.debug(f"{cproc.args} stderr output:\n{cproc.stderr}")
    except subprocess.CalledProcessError as e:
        logger.exception(
            f"{e.cmd} returned error {e.returncode}. "
            f"STDERR:\n{e.stderr}"
        )
        raise
    finally:
        if list_file_path is not None and path.exists(list_file_path):
            remove(list_file_path)

    # Something might be wrong? Those might just be harmless warning?
    # if cproc is not None\
    # and ("Found duplicated MOOV Atom. Skipped it" in cproc.stderr
    #     or "Failed to add index entry" in cproc.stderr):

    props = probe(ffmpeg_output_filename)
    if len(seg_list) * 0.80 < props.get("duration", 0) > len(seg_list) * 20:
        logger.info(
            f"Abnormal duration of {ffmpeg_output_filename}: "
            f"{props.get('duration')}. Removing..."
        )

        remove(ffmpeg_output_filename)
        if method < len(METHOD) - 1:
            logger.info(f"Trying next method... {METHOD[method+1]}")
            return concat(datatype, video_id, seg_list, output_dir,
                            method=method + 1)

    if path.exists(concat_filepath):
        remove(concat_filepath)
    if not path.exists(ffmpeg_output_filename):
        return None
    return ffmpeg_output_filename


def probe(fpath):
    probecmd = ['ffprobe', '-v', 'quiet', '-hide_banner',
                '-show_streams', fpath]
    probeproc = subprocess.run(probecmd, capture_output=True, text=True)
    logger.debug(f"{probeproc.args} stderr output:\n{probeproc.stdout}")

    values = {}
    for line in probeproc.stdout.split("\n"):
        if "duration=" in line:
            val = line.split("=")[1]
            values["duration"] = float(val) if val != "N/A" else 0.0
            continue
        if "codec_name=" in line:
            val = line.split("=")[1]
            values["codec_name"] = val if val != "N/A" else None
            continue

    logger.debug(
        f"{path.basename(fpath)} codec: {values.get('codec_name')}, "
        f"duration: {values.get('duration')}"
    )

    return values


def merge(info, data_dir,
          output_dir=None,
          keep_concat=False,
          delete_source=False):
    if not output_dir:
        output_dir = data_dir

    if not data_dir or not path.exists(data_dir):
        # logger.critical(f"Data directory \"{data_dir}\" not found.")
        return None

    # Reuse the logging handlers from the download module if possible
    # to centralize logs pertaining to stream video handling
    global logger
    logger = logging.getLogger("download" + "." + info['id'])
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        # File output
        logfile = logging.FileHandler(\
            filename=data_dir + sep +  "download.log", delay=True)
        logfile.setLevel(logging.DEBUG)
        formatter = logging.Formatter(\
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        logfile.setFormatter(formatter)
        logger.addHandler(logfile)

        # Console output
        conhandler = logging.StreamHandler()
        conhandler.setLevel(logging.DEBUG)
        conhandler.setFormatter(formatter)
        logger.addHandler(conhandler)

    video_seg_dir = data_dir + sep + "vid"
    audio_seg_dir = data_dir + sep + "aud"

    video_files = collect(video_seg_dir)
    audio_files = collect(audio_seg_dir)

    if not video_files and not audio_files:
        return None

    if len(video_files) != len(audio_files):
        logger.warning("Number of audio and video segments do not match.")

    print_missing_segments(video_files, "_video")
    print_missing_segments(audio_files, "_audio")

    # Determine codec from first file
    vid_props = probe(str(video_files[0]))
    aud_props = probe(str(audio_files[0]))

    ffmpeg_output_path_video = concat(
        vid_props.get("codec_name", "video"),
        info.get('id'),
        video_files,
        data_dir
    )
    ffmpeg_output_path_audio = concat(
        aud_props.get("codec_name", "audio"),
        info.get('id'),
        audio_files,
        data_dir
    )

    if not ffmpeg_output_path_audio or not ffmpeg_output_path_video:
        logger.error(f"Missing video or audio concatenated file!\
Retrying with concat demuxer...")
        return None

    ext = "mp4"
    # Seems like an MP4 container can handle vp9 just fine. Perhaps we don't
    # really need MKV (which doesn't support embedded thumbnails yet anyway).
    # if vid_props.get("codec_name") == "vp9":
    #     ext = "mkv"

    final_output_name = sanitize_filename(
        f"{info.get('author')}_"
        f"[{info.get('download_date')}]_{info.get('title')}_"
        f"[{info.get('video_resolution')}]_{info.get('id')}",
        f".{ext}"
    )

    final_output_file = output_dir + sep + final_output_name

    try_thumb = True
    while True:
        ffmpeg_command = ["ffmpeg", "-hide_banner", "-y",\
                        "-i", f"{ffmpeg_output_path_video}",\
                        "-i", f"{ffmpeg_output_path_audio}"
                        ]
        metadata_cmd = metadata_arguments(info, data_dir,
                                          want_thumb=try_thumb
                                        )
        # ffmpeg -hide_banner -i video.mp4 -i audio.m4a -i thumbnail.jpg -map 0
        # -map 1 -map 2 -c:v:2 jpg -disposition:v:1 attached_pic -c copy out.mp4
        ffmpeg_command.extend(metadata_cmd)
        ffmpeg_command.extend(["-c", "copy", final_output_file])

        try:
            cproc = subprocess.run(ffmpeg_command,
                               check=True,
                               capture_output=True,
                               text=True)
            logger.debug(f"{cproc.args} stderr output:\n{cproc.stderr}")
        except subprocess.CalledProcessError as e:
            logger.debug(
                f"{e.cmd} return code {e.returncode}. STDERR:\n{e.stderr}"
            )

            if try_thumb \
            and 'Unable to parse option value "attached_pic"' in e.stderr:
                logger.error(
                    "Failed to embed the thumbnail into the final video "
                    "file! Trying again without it..."
                )
                try_thumb = False
                if path.exists(final_output_file)\
                and stat(final_output_file).st_size == 0:
                    logger.info("Removing zero length ffmpeg output...")
                    remove(final_output_file)
                continue

        if not path.exists(final_output_file):
            logger.critical("Missing final merged output file! \
Something went wrong.")
            return None
        break

    if path.exists(final_output_file) and stat(final_output_file).st_size == 0:
        logger.critical("Final merged output file is zero length! \
Something went wrong. Try again with DEBUG log level and check for errors.")
        remove(final_output_file)
        return None

    logger.info(f"Successfully wrote file \"{final_output_file}\".")

    if not keep_concat:
        logger.debug(f"Removing temporary audio/video concatenated files...")
        remove(ffmpeg_output_path_audio)
        remove(ffmpeg_output_path_video)

    if delete_source:
        logger.info(f"Deleting source segments...")
        remove(video_seg_dir)
        remove(audio_seg_dir)

    return final_output_file


def print_missing_segments(filelist, filetype):
    """
        Check that all segments are available.
        :param list filelist: a list of pathlib.Path
        :param str filetype: "_video" or "_audio"
    """
    missing = False
    first_segnum = 0
    last_segnum = 0

    if filelist:
        # Get the numbers from the file name
        # filename format is 0000000001_[audio|video].ts
        first_segnum = int(filelist[0].name.split(filetype + ".ts")[0])
        last_segnum = int(filelist[-1].name.split(filetype + ".ts")[0])

    if first_segnum != 0:
        logger.warning(
            f"First {filetype[1:]} segment number starts at {first_segnum} "
            "instead of 0."
        )

    # Numbering in filenames starts from 0
    if len(filelist) != last_segnum + 1:
        logger.warning(
            f"Number of {filetype[1:]} segments doesn't match last segment "
            f"number: Last {filetype[1:]} segment number: "
            f"{last_segnum} / {len(filelist)} total files."
        )
        i = 0
        for f in filelist:
            if f.name != f"{i:0{10}}{filetype}.ts":
                missing = True
                logger.warning(
                    f"Segment {i:0{10}}{filetype}.ts seems to be missing."
                )
                i += 1
            i += 1
    return missing


def metadata_arguments(info, data_path, want_thumb=True):
    cmd = []
    # Embed thumbnail if a valid one is found
    if want_thumb:
        cmd = get_thumbnail_command_prefix(data_path)

    # These have to be placed AFTER, otherwise they affect one stream in particular
    if title := info.get('title'):
        cmd.extend(["-metadata", f"title='{title}'"])
    if author := info.get('author'):
        cmd.extend(["-metadata", f"artist='{author}'"])
    if download_date := info.get('download_date'):
        cmd.extend(["-metadata", f"date='{download_date}'"])
    if description := info.get('description'):
        cmd.extend(["-metadata", f"description='{description}'"])
    return cmd


def get_thumbnail_command_prefix(data_path):
    thumb_path = get_thumbnail_pathname(data_path)
    if not thumb_path:
        return []

    _type = what(thumb_path)
    logger.info(f"Detected thumbnail: {thumb_path}. Type: {_type}.")
    if _type != "jpeg" and _type != "png":
        if _type == "webp":
            try:
                convert_thumbnail(thumb_path, _type)
            except Exception as e:
                logger.error(
                    f"Failed converting thumbnail from {_type} format. {e}"
                )
                return []
        else:
            logger.warning(
                f"Unsupported thumbnail format: {_type}. "
                "Skipping embedding into video."
            )
            return []

    # https://ffmpeg.org/ffmpeg.html#toc-Stream-selection
    return ["-i", f"{thumb_path}",\
            "-map", "0", "-map", "1", "-map", "2",\
            # "-c:v:2", _type,
            # copy probably means no re-encoding again into jpg/png
            "-c:a:2", "copy",\
            "-disposition:v:1",\
            "attached_pic"]


def convert_thumbnail(thumb_path, fromformat):
    try:
        from PIL import Image
    except ImportError as e:
        logger.error(f"Failed loading PIL (pillow) module. {e}")
        raise e

    old_path = str(thumb_path)
    new_name = ".".join((old_path, fromformat))
    rename(old_path, new_name)

    # TODO Pillow can detect and try all available formats
    with Image.open(new_name) as im:
        logger.debug(f"Converting {new_name} to PNG...")
        im.convert("RGB")
        im.save(old_path, "PNG")
        logger.debug(f"Saved PNG thumbnail as {old_path}")


def get_thumbnail_pathname(data_path):
    """Returns Path to a file named "thumbnail" if found in data_path."""
    fl = list(Path(data_path).glob('thumbnail'))
    if fl:
        return fl[0]
    return None


def collect(data_path):
    if not path.exists(data_path):
        logger.warning(f"{data_path} does not exist!")
        return []
    files = [p for p in Path(data_path).glob('*.ts')]
    files.sort()
    return files

def sanitize_filename(name, extension):
    """Remove characters in name that are illegal in some file systems."""
    filename = "".join(c for c in name if 31 < ord(c) and c not in r'<>:"/\|?*')
    # Coerce filename length to 255 characters which is a common limit.
    filename = filename[:255 - len(extension)]
    return filename + extension
