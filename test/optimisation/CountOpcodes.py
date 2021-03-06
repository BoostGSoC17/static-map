#!/usr/bin/python3

#          Copyright Niall Douglas  2015-2017.
#          Copyright Tom Westerhout 2017.
# Distributed under the Boost Software License, Version 1.0.
#    (See accompanying file LICENSE_1_0.txt or copy at
#          http://www.boost.org/LICENSE_1_0.txt)


# Parse x64 assembler dumps and figure out how many opcodes something takes

import sys, os, re

debug = False

# objdump format example:
# 0000000000000000 <_Z5test1v>:
#    0:	55                   	push   %rbp
#    1:	48 89 e5             	mov    %rsp,%rbp
#    4:	be 00 00 00 00       	mov    $0x0,%esi
#    9:	bf 00 00 00 00       	mov    $0x0,%edi
#    e:	e8 00 00 00 00       	callq  13 <_Z5test1v+0x13>
#   13:	be 0a 00 00 00       	mov    $0xa,%esi
#   18:	48 89 c7             	mov    %rax,%rdi
#   1b:	e8 00 00 00 00       	callq  20 <_Z5test1v+0x20>
#   20:	90                   	nop
#   21:	5d                   	pop    %rbp
#   22:	c3                   	retq   


_is_new_function_ = \
    { # ---> 4 zeros in the begining
      # ---> then some unknown number of lower case HEX numbers
      # ---> a space
      # ---> function name enclosed in <>
      # ---> colon :
      'objdump' : lambda l: re.match(r"^0{4}[0-9a-f]+ <.+>:$", l) is not None 

      # ---> line starts with a non-space character
      # ---> something
      # ---> line ends with a colon :
    , 'dumpbin' : lambda l: re.match(r"^[^ ].*:$", l) is not None
    }

_get_function_name_ = \
    { 'objdump' : lambda l: re.match(r"^0{4}[0-9a-f]+ <(.+)>:$", l).group(1)
    , 'dumpbin' : lambda l: re.match(r"^([^ ]+).*:$", l).group(1)
    }

_is_instruction_ = \
    { # ---> at least 2 spaces
      # ---> address, i.e. some HEX numbers
      # ---> colon :
      # ---> more HEX numbers and spaces
      # ---> asm instruction, i.e. a word of latin characters
      # ---> arguments
      'objdump' : lambda l: re.match(r"^[ ]{1,}[0-9a-f]+:\s*[0-9a-f ]+\s*\t[a-z]+.*$", l) \
                                is not None 

      # the same, except that the line starts with exactly two spaces
    , 'dumpbin' : lambda l: re.match(r"^[ ]{2,}[0-9A-F]+:[0-9A-F ]+[a-z]+.*$", l) \
                                is not None
    }

_is_normal_instruction_ = \
    { 'objdump' : lambda l: _is_instruction_['objdump'](l) \
                                and ('nop' not in l) and ('retq' not in l)
    , 'dumpbin' : lambda l: _is_instruction_['dumpbin'](l) \
                                and ('nop' not in l) and ('ret' not in l)
    }

_is_call_instruction_ = \
    { 'objdump' : lambda l: "callq" in l
    , 'dumpbin' : lambda l: "call" in l
    }


def _get_call_target_objdump(l : str) -> str:
    (named, calculated) = \
        re.match(r".*callq\s+(?:[0-9a-f]+\s+<(.+)>$|(\S+).*$)", l).groups()
    if named is not None and calculated is None:
        return named
    elif named is None and calculated is not None:
        return calculated
    return None

_get_call_target_ = \
    { 'objdump' : _get_call_target_objdump
    , 'dumpbin' : lambda l: re.match(r".*call\s+(.+)$", l).group(1)
    }

_is_our_function_ = \
    { 'objdump' : lambda f: lambda l: (f in l) and ('-0x' not in l)
    , 'dumpbin' : lambda f: lambda l: (f in l) and ('?dtor' not in l) \
        and (not l.startswith('@ILT'))
    }


def parse(input_file, file_type : str) -> dict:
    functions = {}
    f   = None
    ops = []

    def save():
        nonlocal f
        nonlocal ops
        if f is not None:
            debug and print("[*] Storing function " + str(f) + " with " 
                + str(len(ops)) + " lines", file=sys.stderr)
            functions[f] = ops
            f   = None
            ops = []
    def append(l : str):
        nonlocal ops
        if f is not None:
            ops.append(l)
    def skip():
        pass

    is_func  = _is_new_function_[file_type]
    is_op    = _is_instruction_[file_type]
    get_name = _get_function_name_[file_type]

    for i, line in filter( lambda t: len(t[1]) > 0, 
                   map(    lambda t: (t[0], t[1].rstrip()), 
                   enumerate(input_file, start=1) )):
        debug and print("[*] Line " + str(i) + " is '" + line + "'", 
            file=sys.stderr)
        if is_func(line):
            save()
            f = get_name(line)
            debug and print("[*] Line " + str(i) 
                + ": new objdump function: " + f, file=sys.stderr)
        elif is_op(line):
            if f is not None:
                append(line)
            else:
                skip()
        else:
            skip()
    save()
    return functions


def find_opcodes(name : str, functions : dict, file_type : str) -> tuple:
    is_match = _is_our_function_[file_type](name)
    all_matches = list(filter(lambda t: is_match(t[0]), functions.items()))
    if len(all_matches) == 0:
        return name, None
    if len(all_matches) > 1:
        print("[*] Matching functions: ", list(map(lambda t: t[0], 
            all_matches)), file=sys.stderr)
    assert len(all_matches) == 1
    return all_matches[0]


def _inline_all_impl_(operation : str, functions : dict, 
    black_list : set, is_a_call, get_target,
    allow_recursion : bool):

    if not is_a_call(operation):
        debug and print("[*] '" + operation + "' is not a call operation.",
            file=sys.stderr)
        return [operation]

    debug and print("[*] '" + operation + "'...", file=sys.stderr)
    target = get_target(operation) 
    debug and print("[*] Expanding " + repr(target) + "...", file=sys.stderr)

    if (not allow_recursion) and (target in black_list):
        debug and print("[*] '" + target + "' in black list.", file=sys.stderr)
        return [operation]

    if (target not in functions):
        debug and print("[*] No info on " + repr(target) + ".", file=sys.stderr)
        return [operation]

    black_list.add(target)
    opcodes = functions[target]
    return sum(map(lambda op: _inline_all_impl_(op, functions, black_list,
        is_a_call, get_target, allow_recursion), opcodes), [])


def inline_all(name : str, functions : dict, file_type : str,
    allow_recursion : bool = False):

    is_a_call  = _is_call_instruction_[file_type]
    get_target = _get_call_target_[file_type]
    debug and print("Initially: ", functions[name], file=sys.stderr)
    return sum(map(lambda op: _inline_all_impl_(op, functions, {name},
        is_a_call, get_target, allow_recursion), functions[name]), [])


def count_opcodes(input_file : str, func : str):
    functions = {}
    file_type = 'objdump' if os.name == 'posix' else 'dumpbin'

    # Read all the functions
    with open(input_file, "rt") as ih:
        functions = parse(ih, file_type)

    # Find the one we're interested in
    name, opcodes = find_opcodes(func, functions, file_type)
    if opcodes is None:
        return -1, None

    # Inline as much as possible
    opcodes = inline_all(name, functions, file_type, False)

    # Calculate number of operations
    is_normal = _is_normal_instruction_[file_type]
    count = sum(map(is_normal, opcodes))

    return count, opcodes
