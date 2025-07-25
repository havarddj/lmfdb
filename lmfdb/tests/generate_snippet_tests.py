# Helper function for generating test files

from pathlib import Path
import yaml
import argparse
import os, sys
from sage.all import sage_eval
from difflib import ndiff
import pexpect, pexpect.replwrap # for communicating with processes
import re
from time import sleep

# to ensure that imports work correctly when called from ./lmfdb: 
sys.path.insert(0, "/".join(os.path.realpath(__file__).split("/")[0:-3]))


exec_dict = {'sage': 'sage --simple-prompt',
             'magma': 'magma -b',
             'oscar': 'julia',
             'gp': "gp -D prompt='gp>' -D breakloop=0 -D colors='no,no,no,no,no,no,no' -D readline=0"}
prompt_dict = {'sage': 'sage:', 'magma': 'magma>', 'oscar': 'julia>', 'gp': 'gp>'}
comment_dict = {'magma': '//', 'sage': '#',
                         'gp': '\\\\', 'pari': '\\\\', 'oscar': '#', 'gap': '#'}



# TODO: this should be run by CI when it detects changes to yaml files
# TODO: also write CI to run on crontab, testing this every X weeks


def _setup_test_dir(yaml_file_path=None):
    """ Return dictionary with pair(s) 'yaml-file-path': 'test-file-path'.
    If yaml-file-path is none, search through all code*.yaml files in ./lmfdb
    """
    test_dir = Path('./lmfdb/tests/')
    snippet_dir = (test_dir / 'snippet_tests' )
    if not snippet_dir.exists():
        snippet_dir.mkdir()

    lmfdb_dir = test_dir.parent

    if not test_dir.exists():
        raise Exception("Please run in same directory as test.sh")

    if yaml_file_path == None:
        code_paths = lmfdb_dir.rglob("code*.yaml")
    else:
        code_paths = [Path(yaml_file_path)]
        assert code_paths[0].exists(), f"Specified path {yaml_file_path} does not exist"
        
    path_dict = {}
    for path in code_paths:
        try:
            rel_path = path.relative_to(lmfdb_dir)
        except ValueError:
            print(f"Warning: could not resolve relative path of {path}")
            continue
        new_dir = snippet_dir / rel_path.parent
        path_dict[path] = new_dir
        if not new_dir.exists():
            print(f"Directory {new_dir} does not exist, creating.")
            new_dir.mkdir(parents=True)
    return path_dict

def _start_snippet_procs(langs):
    """ Return dict where keys are languages in 'langs'
    and values are pexpect repl processes 
    """
    processes = {}
    for lang in langs:
        if lang == 'oscar':
            print("Loading Oscar, this may take a while:")
            spawn = pexpect.spawn(exec_dict['oscar'], ['-q', '--color=no', '--banner=no'],
                                  echo=False, env=os.environ | {'TERM':'dumb'},
                                  encoding="utf8")
            # for ease of debugging julia output
            spawn.logfile = sys.stdout
            
            processes['oscar'] = pexpect.replwrap.REPLWrapper(spawn, 'julia>', None)
            processes['oscar'].run_command("using Oscar", timeout=60*10)
            print("\nOscar loaded")
        elif lang == 'magma':
            # avoid '>' being detected as prompt
            processes['magma'] = pexpect.replwrap.REPLWrapper(exec_dict[lang],
                                                              '>',
                                                              f'SetPrompt("{prompt_dict[lang]}");',
                                                              prompt_dict[lang])
        else:
            processes[lang] = pexpect.replwrap.REPLWrapper(exec_dict[lang], prompt_dict[lang] , None)
    return processes


def _eval_code_file(data, lang, proc, logfile):
    """ Evaluate code in 'data' using process 'proc' in language
    'lang', writing output to 'logfile'
    """
    eval_str = ""
    cmt = comment_dict[lang]
    lines = [l for l in data.splitlines() if l != '' and cmt not in l[:4]]
    with logfile.open('w') as f:
        proc.child.logfile = f
        for line in lines:
            try:
                proc.run_command(line, timeout=60)
            except:
                print("Timeout while running line:")
                print(line)

    # # remove stray ANSI escape characters
    # with logfile.open('r') as f:
    #     res = 
    #     ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    #     ansi_escape.sub('', res)
    #     return eval_str



def create_snippet_tests(yaml_file_path=None, ignore_langs = [], test = False):
    """
    Create tests for snippet files in yaml_file_path if not None, else for all
    code*.yaml files in the lmfdb, except for those with languages in ignore_langs
    """

    path_dict = _setup_test_dir(yaml_file_path)

    from lmfdb.app import app
    
    app.config["TESTING"] = True
    # Ensure secret key is set for testing (required for session functionality like flash messages)
    if not app.secret_key:
        app.secret_key = "test_secret_key_for_testing_only"
    my_app = app
    tc = app.test_client()
    app_context = my_app.app_context()
    app_context.push()
    import lmfdb.website

    assert lmfdb.website
    from lmfdb import db

    langs = set()
    for code_file in path_dict.keys():
        contents = yaml.load(code_file.open(), Loader=yaml.FullLoader)
        if 'snippet_test' in contents:
            langs |= set(contents['prompt'].keys())
    langs -= set(ignore_langs)
    if 'pari' in langs:
        langs.remove('pari'); langs.add('gp')

    print("Langs are", langs)
    # start process for languages to be tested
    processes = _start_snippet_procs(langs)
    print("Spawned processes for ", langs)
    
    for code_file, test_dir in path_dict.items():
        contents = yaml.load(code_file.open(), Loader=yaml.FullLoader)
        if 'snippet_test' not in contents:
            print("(Skipping", str(code_file) + ", no key 'snippet_test' found)")
            continue
        snippet_test = contents['snippet_test']
        
        # MAYBE: put this in a separate function
        for _, items in snippet_test.items():
            label = items['label']
            snippet_langs = {'gp' if k == 'pari' else k for k in contents['prompt'].keys()}
            snippet_langs &= langs # intersection of sets

            for lang in snippet_langs:
                url = items['url'].format(lang=lang)

                
                filename = code_file.stem + "-" + label + "-" + lang + ".log"
                if test:
                    old_file = filename
                    filename += ".copy"
                logfile = Path(test_dir / filename)
                if not test:
                    print("Writing data to", str(logfile))
                
                if not logfile.exists():
                    logfile.touch()

                data = tc.get(url).get_data(as_text=True)

                with logfile.open('w') as f:
                    header  = comment_dict[lang] + " Code taken from https://beta.lmfdb.org/" + str(url) +'\n\n'
                    f.write(header)
                
                _eval_code_file(data, lang, processes[lang], logfile)

                with logfile.open('r') as f:
                    if "error" in f.read():
                        print(f"\x1b[31mWARNING\x1b[0m: found error in ./{logfile}")
                
                if test:
                    old_path = Path(test_dir / old_file)
                    assert old_path.exists(), f"Could not find original file at ./{old_file}."
                    with old_path.open('r') as f:
                        old_str = f.read()
                    with logfile.open('r') as f:
                        if f.read() == old_str:
                            print(f"No change in {old_path}")
                        else:
                            print(f"Change in {old_path}, compare with {logfile}")
                            continue
                    # now delete file
                    logfile.unlink()
                

            

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Generate snippet tests")
    parser.add_argument("cmd", help="*generate* test files or run *test*s", choices=['generate', 'test'])
    parser.add_argument("-i", "--ignore", help="ignore languages", action='append', nargs='+', default=[])
    parser.add_argument("-f", "--file", help="run on single file", type=str)
    
    args = parser.parse_args()
    if args.file:
        yaml_path = Path(args.file) 
        assert yaml_path.exists(), f"File {args.file} does not exist."
    else:
        yaml_path = None
    ignore_langs = [l[0] for l in args.ignore]
    create_snippet_tests(yaml_path, ignore_langs, test= args.cmd == 'test')
        

