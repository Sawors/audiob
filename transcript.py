#!/bin/env python3

import subprocess
from sys import argv
import math
import json
import os
from os import path
import whisper
from zipfile import ZipFile
from time import sleep
import tempfile

###############################################################################

OUTPUT_DIR="output"

MODEL = "medium.en"
ITERATIONS = 1

ARCH_AUDIO = "audio.mp3"
ARCH_TRANSCRIPT = "transcript.json"

###############################################################################

_no_color_print=False

class Color:
    GREY   = "\033[0;90m"
    RED     = "\033[0;31m"
    GREEN   = "\033[0;32m"
    YELLOW  = "\033[0;33m"
    BLUE    = "\033[0;34m"
    MAGENTA = "\033[0;35m"
    CYAN    = "\033[0;36m"
    WHITE   = "\033[0;37m"
    RESET   = "\033[0m"

    def from_int(value:int) -> str:
        return f"\033[0;{value}m"

    def color(str:str, color:str):
        return color+str+Color.RESET if not _no_color_print else str

class WordFragment(dict):
    word: str
    start: float
    end: float
    # Yay ! Java memories !
    def __init__(self, word:str,start:str,end:str):
        dict.__init__(self, word=word, start=start, end=end)
        self.end = end
        self.start = start
        self.word = word
        

def print_progess_bar(
        progress:float, 
        length:int, 
        prepend="[", 
        append="] {:.1%}",
        fill="━",
        empty="·",
        current=" ",
        adapt_size=True,
        prepend_end=None,
        append_end="] done!",
        fill_color=Color.from_int(92),
        current_color=Color.from_int(92),
        empty_color=Color.GREY,
        done_color=Color.CYAN
        ):
    """Styles :
    classic: 
        fill="━", 
        empty="·", 
        current=" "
    pacman: 
        fill="-", 
        empty="·", 
        current=" ᗧ"
    """
    term_width = 1920
    try:
        term_width = os.get_terminal_size()[0]
    except:
        pass
    c_progess = min(max(progress,0),1)
    last_iter = c_progess == 1

    append = append.format(progress)

    resized_length = length
    pre = prepend_end if last_iter and not prepend_end is None else prepend
    app = append_end if last_iter and not append_end is None else append
    barless_content = f"{pre}{app}"
    if adapt_size:
        resized_length = min(length,max(2,term_width-len(barless_content)))
    empty_length = math.floor((1-c_progess)*resized_length)
    fill_length = math.ceil(c_progess*resized_length)
    fill_str = (f"{(fill_length-len(current))*fill}{current}" if not last_iter else fill_length*fill) if fill_length > 0 else ""
    raw_bar = f"{pre}{fill_str}{empty_length*empty}{app}"
    bar = f"{pre}{Color.color(fill_str,fill_color)}{Color.color(empty_length*empty,empty_color)}{app}"
    if last_iter:
        bar = f"{pre}{Color.color(f'{fill_str}{empty_length*empty}',done_color)}{app}"
    print(
        bar + (" "*max(0,term_width-len(raw_bar))),
        end="\r" if not last_iter else "\n"
        )

def get_pretty_time_print(seconds:int, separator=":") -> str:
    minutes=math.floor(seconds/60)
    hours=math.floor(seconds/3600)
    sec=seconds-((hours*3600)+(minutes*60))
    
    h_dp=(str(int(hours)) if hours > 0 else '').zfill(2)
    m_dp=(str(int(minutes)) if minutes > 0 else '').zfill(2)
    s_dp=(str(int(sec)) if sec > 0 else '').zfill(2)
    return f"{h_dp}{separator}{m_dp}{separator}{s_dp}"

def get_filename(file:str, keep_extension=True) -> str:
    f_split = file.split(path.sep)
    filename = f_split[len(f_split)-1]
    if keep_extension:
        return filename
    return filename.split(".")[0]

def as_output_file(file:str, extension=".json") -> str:
    output_dir_path = f"{path.dirname(__file__)}{path.sep}{OUTPUT_DIR}"
    #f_clean = f.replace(" "," ")
    return f"{output_dir_path}{path.sep}{get_filename(file)}{extension}"

def transcribe(input_file:str, model=MODEL, iterations=ITERATIONS) -> list:
    if input_file is None:
        print("Please provide an input file!")
        return
    if not input_file.startswith(path.sep):
        input_file=f"{os.getcwd()}{path.sep}{input_file}"
    transcription_queue=[]
    if path.isdir(input_file):
        for d, _, f in os.walk(input_file):
            for file in f:
                transcription_queue.append(f"{d}{path.sep}{file}")
    elif path.isfile(input_file):
        transcription_queue.append(input_file)
    else:
        print("Input file not found!")
        return
    for index, f in enumerate(transcription_queue):
        raw_text=""
        data={}

        if not path.isfile(f):
            print(f"File {filename} not found!")
            continue
        
        file_size = path.getsize(f)
        # https://github.com/jianfch/stable-ts 
        import stable_whisper as whisper
        model = whisper.load_model(model)
        print("Transcription beginning...")
        for i in range(iterations):
            print(f"iteration {i+1}/{iterations}")
            # iterate the transcription multiple times
            data = model.transcribe(
                f, 
                max_initial_timestamp=None,
                word_timestamps=True,
                suppress_silence=False,
                #initial_prompt=f"This is an audio from an audiobook or a song which is named {get_filename(f,keep_extension=False)}. Try to find the most precises word timestamps as possible and be as precise as possible when detecting words",
                #denoiser="demucs",
                vad=False,
                #no_speech_threshold=0.8,
                #min_word_dur=0.5,
                #nonspeech_error=0.3,
                use_word_position=True,
                #vad=True,
                )
        data = (
                model
                .align(f, data, language=data.language)
                .split_by_length(max_words=24)
                ).adjust_by_silence(f)
        # https://github.com/jianfch/stable-ts/blob/3bc76b98d52bdeae861e29d0e30c972a35392617/stable_whisper/result.py#L829
        print("Refining the result...")
        #data.adjust_by_silence(f)
        model.refine(f,data,precision=0.05)
        print("Done !")
        data_list = []
        for t in data.segments:
            seg = []
            for w in t.words:
                seg.append(
                WordFragment(
                    word=w.word,
                    start=w.start,
                    end=w.end
                )
            )
            data_list.append(seg)
        return data_list

def play_sync(input_file):
    split = input_file.split(os.path.sep)
    filename = split[len(split)-1]
    data = []
    temp = tempfile.NamedTemporaryFile(suffix=".mp3")
    with ZipFile(input_file, mode="r") as archive:
        data = json.loads(archive.read(ARCH_TRANSCRIPT))
        temp.write(archive.read(ARCH_AUDIO))
    proc = subprocess.Popen(["paplay",temp.name])
    time_match = []
    prev = 0
    offset = data[0][0]["start"]
    ##
    player_delay = 0
    word_preshot_delay = 0.1
    ##
    sleep(max(player_delay+offset,0))
    for index, seg in enumerate(data):
        segment_start = seg[0]["start"]
        segment_end = seg[len(seg)-1]["end"]
        next_seg = data[index+1] if index < len(data)-1 else None
        seg_text = ""
        time_match = f"[{get_pretty_time_print(segment_start)} - {get_pretty_time_print(segment_end)}]"
        seg_whole_text = [w["word"] for w in seg]
        for indexw, w in enumerate(seg):
            nxt = seg[indexw+1] if indexw < len(seg)-1 else next_seg[0] if not next_seg is None else None
            start = w["start"]
            end = w["end"]
            duration = end-start
            blank_after = (nxt["start"]-end) if not nxt is None else 0
            words_before = "".join(seg_whole_text[0:indexw])
            word = w["word"]
            words_after = "".join(seg_whole_text[indexw+1:len(seg)])
            print(
                Color.color(time_match,Color.GREEN)+
                Color.color("  | ",Color.WHITE)+
                Color.color(words_before,Color.GREY)+
                Color.color(word,Color.CYAN)+
                Color.color(words_after,Color.WHITE)
                , end="\r")
            #print(("" if indexw < len(seg)-1 else "\n")+"{0:.2f}".format(segment_start)+" - {0:.2f}  | ".format(segment_end)+seg_text, end="\r")
            sleeptime = duration+blank_after
            if word_preshot_delay > 0 and sleeptime >= word_preshot_delay:
                sleep(sleeptime-word_preshot_delay)
                word_preshot_delay = 0
            else:
                sleep(sleeptime)    
            if indexw >= len(seg)-1:
                print(
                Color.color(time_match+"  | ",Color.WHITE)+
                Color.color(words_before+word+words_after,Color.GREY)
                , end="\n")
    temp.close()

def main(args:list):
    input_file=next(filter(lambda k: not k.startswith("-"),args))
    arch_name = f"{get_filename(input_file,keep_extension=False)}_audiob"
    zip_file = as_output_file(arch_name,extension=".zip")
    if input_file is None or not path.exists(input_file):
        print("Please provide an input file!")
        return
    model = MODEL
    iterations = ITERATIONS
    do_trans = True
    do_play = True
    for a in args:
        # len(args) <= 1 or not ("--usecache" in args or "-c" in args)
        # len(args) <= 1 or not ("--transcribe" in args or "-t" in args)
        if a == "--play" or a == "-p":
            do_trans = False
            do_play = True
        if a == "--transcribe" or a == "-t":
            do_trans = True
            do_play = False
        if a.startswith("--model=") or a.startswith("-m="):
            sp=a.split("=")
            model=sp[len(sp)-1]
        if a.startswith("--iter=") or a.startswith("-i="):
            sp=a.split("=")
            iterations=int(sp[len(sp)-1])

    if do_trans:
        data = transcribe(input_file,model=model,iterations=iterations)
        output_file = as_output_file(input_file)
        # with open(output_file, "w") as out:
        #     json.dump(data,out,indent=2)
        with ZipFile(zip_file, mode="w") as archive:
            archive.write(input_file,arcname=ARCH_AUDIO)
            archive.writestr(ARCH_TRANSCRIPT, json.dumps(data))
    if do_play:
        play_sync(input_file if input_file.endswith(".zip") else zip_file)

    
if __name__ == "__main__":
    main(argv[1:])
