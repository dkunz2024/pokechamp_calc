import json
import requests #grab from pokeAPI
import math #math.floor()
from pathlib import Path #caching
from datetime import datetime #check cache timestamps
import time # time.sleep() for set retrieval from API
import readline # for tab autocompletion
from enum import Enum # for colors
import pandas as pd # for table output

class COLORS(Enum):
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    RESET = 0

# options
CACHE_DIR = ".cache/"

# constants
POKEMON_ENDPOINT = "https://pokeapi.co/api/v2/pokemon/"
STAT_NAMES = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]
NUM_STATS = len(STAT_NAMES)
MAX_SP = 32
POS_NATURE_MULTIPLIER = 1.1
NEG_NATURE_MULTIPLIER = 0.9
LEVEL = 50
COMMANDS = [
    'help',
    'add',
    'team-add',
    'ls',
    'clear',
    'speed-compare',
    'summary',
    'quit'
]

# for automation of output colors
def color_text(text, color: COLORS):
    return f"\033[{color.value}m{text}\033[{COLORS.RESET.value}m"

# for tab auto-completion of user input
def make_completer(commands):
    def completer(text, state):
        options = [cmd for cmd in commands if cmd.startswith(text)]
        if state < len(options):
            return options[state]
        else:
            return None
    return completer
readline.parse_and_bind("tab: complete")
readline.set_completer_delims(
    readline.get_completer_delims().replace('-', '')
)

def get_pokemon(name):
    
    # first, check the cache for a previous API pull
    filename = name + ".json"
    filepath = Path(CACHE_DIR + filename)
    if filepath.exists():
        print(color_text("opening cached file: "+str(filepath), COLORS.GREEN))
        stat = filepath.stat()
        print(color_text("creation timestamp: "+str(datetime.fromtimestamp(stat.st_ctime)), COLORS.YELLOW))
        with filepath.open("r") as f:
            data = f.read()
            data = json.loads(data)
            return data
    else: 
        # grab new entry from the pokeAPI
        url = POKEMON_ENDPOINT + name + "/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # create the cached file
            print(color_text("no cached file, creating: "+str(filepath), COLORS.RED))
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return data
        except requests.exceptions.HTTPError as http_err:
            print(color_text(f"HTTP error occurred: {http_err}", COLORS.RED))
        except Exception as e:
            print(color_text(f"ERR: {e}", COLORS.RED))
    return None

def add_n_pokemon(pokemon, n:int=0):
    
    # set autocomplete to pokemon names in cache
    cached_names = [file.name.removesuffix(".json") for file in Path(CACHE_DIR).iterdir() if file.is_file()]
    readline.set_completer(make_completer(cached_names))

    # loop until n pokemon
    while(True):
        print(color_text("Enter 'q' to quit.", COLORS.RED), color_text("Enter 'help' for help.", COLORS.CYAN))
        pokemon_name = str(input("Input the name of the pokemon to add: ")).lower()
        if(pokemon_name=="q"):
            if(n==0):
                break
            else:
                print(n-len(pokemon), " pokemon are still needed for this option.\n", end="")
                continue
        elif(pokemon_name=="help"):
            print(color_text("For megas, attach '-mega'. Ex: froslass-mega, charizard-mega-y", COLORS.CYAN))
            print(color_text("For forms, attach region name. Ex: raichu-alola, zoroark-hisui, tauros-paldea-blaze-breed", COLORS.CYAN))
            print(color_text("Others include:", COLORS.CYAN))
            print(color_text("- basculegion-male, basculegion-female", COLORS.CYAN))
            print(color_text("- rotom-wash, rotom-heat, etc.", COLORS.CYAN))
            print(color_text("- mimikyu-disguised, mimikyu-busted", COLORS.CYAN))
            print(color_text("- aegislash-shield, aegislash-blade", COLORS.CYAN))
            print(color_text("- morpeko-full-belly, morpeko-hangry", COLORS.CYAN))
            print(color_text("- maushold-family-of-three, maushold-family-of-four", COLORS.CYAN))
            continue
        data = get_pokemon(pokemon_name)
        if(data is not None):
            pokemon.append(data)
        if(len(pokemon)>=n and n!=0):
            break

def get_name(mon):
    return mon["name"].strip()

def get_base_stats(mon):
    all_stats = mon["stats"]
    stat_values = [None]*NUM_STATS
    for i, stat in enumerate(all_stats):
        stat_values[i] = stat["base_stat"]
        assert(stat["stat"]["name"]==STAT_NAMES[i])
    return stat_values

# calculates a single stat, given nature and training
def calc_stat(stat, sp, N, HP=False):
    ret = 2*stat+31
    ret = ret*LEVEL
    ret = math.floor(ret/100)
    if(HP):
        ret = ret+LEVEL+10+sp
    else:
        ret = ret+5+sp
        ret = math.floor(ret*N) # Nature
    return ret

def calc_leveled_stats(stats, sp=None, N=None):
    # SP are the points we can use like EVs for training. N is our nature
    if(sp==None):
        sp = [0]*NUM_STATS
    if(N==None):
        N = [1]*(NUM_STATS-1)

    # calc stats (HP is different)
    stats = [stat for stat in stats] # avoid mutation
    stats[0] = calc_stat(stats[0], sp[0], 1, True)
    for i in range(1, NUM_STATS):
        stats[i] = calc_stat(stats[i], sp[i], N[i-1]) 
    return stats

def summary(pokemon):
    if(pokemon==[]):
        print(color_text("No pokemon selected.", COLORS.RED))
        return

    for mon in pokemon:
        stats = get_base_stats(mon)
        calc_stats = calc_leveled_stats(stats)
        print(color_text(get_name(mon), COLORS.CYAN))
        for i, stat in enumerate(STAT_NAMES):
            print(color_text("- "+stat+": "+str(calc_stats[i]), COLORS.WHITE))

def speed_compare(pokemon):
    if(pokemon==[]):
        print(color_text("No pokemon selected.", COLORS.RED))
        return

    df = pd.DataFrame(columns=["name", "min", "base", "maxSP", "max", "maxSPscarf", "maxscarf"])
    for mon in pokemon:
        base_speed = get_base_stats(mon)[NUM_STATS-1]
        base = calc_stat(base_speed, 0, 1)
        maxSP = calc_stat(base_speed, MAX_SP, 1)
        maxSPN = calc_stat(base_speed, MAX_SP, POS_NATURE_MULTIPLIER)
        minSPN = calc_stat(base_speed, 0, NEG_NATURE_MULTIPLIER)
        df.loc[len(df)] = [get_name(mon), minSPN, base, maxSP, maxSPN, math.floor(maxSP*1.5), math.floor(maxSPN*1.5)]
    print(df.sort_values('base', ascending=False).to_string(index=False))

def main():
    
    # init
    pokemon = []
    cmd = ""
    main_completer = make_completer(COMMANDS)
    need_input = True 

    # main loop
    while(1):

        # skip input if we have autocompleted (else block at the end)
        if(need_input):
            readline.set_completer(main_completer)
            cmd = input(color_text("]}: ", COLORS.YELLOW))
        else:
            need_input = True
        
        # handle command
        if(cmd=="help"):
            print(color_text("Use TAB for autocompletion", COLORS.CYAN))
            for cmd in COMMANDS:
                print(color_text("- "+cmd, COLORS.WHITE))
        elif(cmd=="add"):
            add_n_pokemon(pokemon)
        elif(cmd=="ls"):
            print(color_text(str(len(pokemon))+" pokemon selected. ", COLORS.GREEN))
            for mon in pokemon:
                print(color_text(get_name(mon), COLORS.WHITE))
        elif(cmd=="speed-compare"):
            speed_compare(pokemon)
        elif(cmd=="summary"):
            summary(pokemon)
        elif(cmd=="clear"):
            pokemon = []
        elif(cmd=="quit"):
            break
        elif(cmd=="team-add"):
            cmd = input("What is the filepath for your team? ")
            with open(cmd, "r") as f:
                for line in f:
                    pokemon.append(get_pokemon(line.strip()))
        #================================================================
        # autocomplete to the first available command
        else:
            cmd = main_completer(cmd, 0)
            if(cmd is None):
                print(color_text("Invalid command.", COLORS.RED))
            else:
                print(color_text("Autocompleted to: "+cmd, COLORS.RED))
                need_input = False

    return 0

main()
