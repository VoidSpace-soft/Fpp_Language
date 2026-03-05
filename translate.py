#!/usr/bin/env python3

import os
import sys
import re

def lex(code):
    # 1. Define your token types using Regex
    # Note: Order matters! (e.g., check for 'var' before general 'IDENT')
    token_specification = [
        ('NUMBER',     r'\d+'),           # Integer
        ('COMMENT',    r'//.*(?:\r?\n|$)'),
        ('STRING',     r'"[^"]*"'),       # String literals
        ('MODULO',     r'\%'),
        ('VOLAT',      r'\bvolatile\b'),
        ('POP',        r'\bdelete\b'),
        ('VAR',        r'\bvar\b'),       # Variable declaration keyword
        ("STRUCT",     r"\bstructure\b"),
        ("SIZE",       r"\bsize\b"),
        ("CALL",       r"\blinked\b"),
        ("RPMOVE",     r"\|\-\|"),
        ('PARAM',      r'\@'),
        ('PMOVE',      r'\&\|'),
        ('MOVETA',     r'>\|'),
        ('MOVETAL',    r'\|<'),
        ('TORAX',      r'\:\|'),
        ('FILTER',     r"\:"),
        ('MOVFA',      r"\|>"),
        ('ANON',       r"\~>"),
        ('LSHIFT',     r'<<'),            # Assignment/Input
        ('RSHIFT',     r'>>'),            # Transfer/Output
        ('LPARAM',     r'\('),            # Math open
        ('INC',        r'\+\+'),
        ('DEC',        r'\-\-'),
        ('RPARAM',     r'\)'),            # Math close
        ('PLUS',       r'\+'),            # Addition
        ('MINUS',      r'-'),             # Subtraction
        ('DIV',        r'\/'),
        ('MUL',        r'\*'),
        ('EQUAL',      r'\=\='),
        ('NEQUAL',     r'\!\='),
        ('BELOWEQ',    r'\<='),
        ('ABOVEEQ',    r'\>='),
        ('ABOVE',      r'\>'),
        ('BELOW',      r'\<'),
        ('GT',         r'\bfunc\b'),            # Block start / Label
        ('LT',         r'\}'),            # Block end / Return
        ('SEMICOLON',  r';'),             # Terminator
        ('IDENT',      r'[a-zA-Z_][\w.]*'),  # Identifiers (variable/function names)
        ('WHITESPACE', r'[ \t\n]+'),    # Skip spaces, tabs, and newlines
        ('MISMATCH',   r'.'),             # Any other character (error)
    ]

    # 2. Compile the regex into one master pattern
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    
    tokens = []
    # 3. Iterate through the code and find matches
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        
        if kind in ['WHITESPACE', "COMMENT"]:
            continue
        elif kind == 'MISMATCH':
            raise RuntimeError(f'Unexpected character: {value}')
        
        # Strip quotes from strings for easier parsing later
        if kind == 'STRING':
            value = value
            
        tokens.append((kind, value))
    
    return tokens

def getop(op):
    ops = {
        "je":"jne",
        "jne":"je",
        "jna":"ja",
        "ja":"jna"
    }

def parse(file):
    code = open(file, 'r').read()
    tokens = lex(code)
    par = ["pa", "pb", "pc", "pd"]
    result = ""
    vardata = ""
    strucdefs = ""
    variables = {
        "stdout":["stdout", 512],
        "return":["return_v", 512],
        "endl":["endl", 8],
        "uva":["uva", 512],
        "uvb":["uvb", 512],
        "uvc":["uvc", 512],
        "uvd":["uvd", 512],
    }
    subs = {}
    n = 0
    ifno = 0
    ifnol = [0 for i in range(10)]
    cif = 0
    wno = 0
    wnol = [0 for i in range(10)]
    cw = 0
    ccond = ""
    strucs = {}
    initdata = ""
    lds = []
    lds2 = {}
    lv = 0
    while n < len(tokens):
        token = tokens[n]
        kind, value = token[0], token[1]
        if value == "using":
            code = "\n" + open("crates/"+tokens[n+1][1], 'r').read() + "\n"+code
        n += 1
    n = 0
    code2 = f"""
structure Double
    v@Double 1
;

structure Byte
    v@Integer 1
;
{code}
"""
    code = code2
    tokens = lex(code)
    while n < len(tokens):
        token = tokens[n]
        kind, value = token[0], token[1]
        if kind == "SEMICOLON":
            result += "\n    call output\n    call clean_regs\n"
        elif kind == "STRING":
            pass
        elif kind == "INC":
            var = tokens[n-1][1]
            result += f"""
    inc qword [{variables[var][0]}]
"""
        elif kind == "DEC":
            var = tokens[n-1][1]
            result += f"""
    dec qword [{variables[var][0]}]
"""
        elif kind == "FILTER":
            val2 = tokens[n+1][1]
            if val2 == "if":
                result += f"""
    {ccond} end_if{ifno}
"""
                ifnol[cif] = ifno
                cif += 1
                ifno += 1
            elif val2 == "while":
                # ccond currently holds 'ja' (the inverse of <)
                # If z is NOT less than 10, jump to the end
                result += f"    {ccond} end_while{wno}\n"
                
                # Store this wno so 'end while' knows where to go
                wnol[cw] = wno
                cw += 1
                wno += 1
            elif val2 in variables:
                result += f"""
    mov qword [{variables[val2][0]}], rax
"""
                if val2 == "return":
                    result += """
    ret
"""
        elif value == "stdint":
            result += """
    call int_to_ascii
"""
        elif kind == "TORAX":
            val = tokens[n-1]
            var = 0
            if val[0] == "STRING":
                var = f'"{val[1][1:-1]}"'
            elif val[0] == "NUMBER":
                var = int(val[1])
            else:
                var = f"[{variables[val[1]][0]}]"
            result += f"""
    mov rax, {var}
"""
        elif kind == "MOVETA":
            var = variables[tokens[n-1][1]]
            size = tokens[n+1][1]
            if size in variables:
                size = f"[{variables[size][0]}]"
            result += f"""
    lea rsi, [{var[0]}]
    lea rdi, [rax]
    mov rcx, {size}
    rep movsb
"""
        elif value == "end":
            thing = tokens[n+1][1]
            if thing == "if":
                cif -= 1
                result += f"""
end_if{ifnol[cif]}:
"""
            elif thing == "while":
                cw -= 1
                current_wno = wnol[cw]
                result += f"""
    jmp loopback{current_wno}
end_while{current_wno}:
"""
            elif thing == "func":
                result += """
ret
"""
        elif value == "clean":
            var = tokens[n+1][1]
            result += f"""
    lea rdi, {variables[var][0]}
    xor al, al
    mov rcx, {variables[var][1]}
    cld
    rep stosb
"""
        elif kind == "RPMOVE":
            fname = tokens[n-1]
            if fname[0] != "IDENT":
                print(f"Unknown func '{fname[1]}'")
                sys.exit(1)
            result += f"""
    lea rax, [rel {fname[1]}_s]
"""
        elif kind == "CALL":
            result += """
    call rax
"""
        elif kind == "MOVFA":
            val2 = tokens[n+1][1]
            var2 = variables[val2]
            prior = tokens[n-1][1]
            if prior in variables:
                prior = f"[{variables[prior][1]}]"
            result += f"""
    lea rsi, [rax]
    lea rdi, [{var2[0]}]
    mov rcx, {prior}
    rep movsb"""
            if val2 == "return":
                result += "\nret\n"

        elif kind == "RSHIFT":
            val1 = tokens[n-1][1]
            if not tokens[n-1][0] == "IDENT":
                print(f"RSHIFT expects IDENT as var name one not '{tokens[n-1][0]}'")
                sys.exit(1)
            val2 = tokens[n+1][1]
            if not tokens[n+1][0] == "IDENT":
                print(f"RSHIFT expects IDENT as var name two not '{tokens[n-1][0]}'")
                sys.exit(1)
            var1 = variables[val1]
            var2 = variables[val2]
            prior = var1[1]
            if var2[1] < prior: prior = var2[1]
            result += f"""
    lea rdi, {var2[0]}
    xor al, al
    mov rcx, {var2[1]}
    cld
    rep stosb
    lea rsi, [{var1[0]}]
    lea rdi, [{var2[0]}]
    mov rcx, {prior}
    rep movsb"""
            if val2 == "return":
                result += "\nret\n"

        elif value == "stdin_int":
            result += """
    call input_to_int
"""
        elif value == "stdin_ascii":
            result += """
    call get_raw_input
"""

        elif kind == "LSHIFT":
            im = tokens[n+1]
            var = tokens[n-1][1]
            if not tokens[n-1][0] == "IDENT":
                print(f"LSHIFT expects IDENT as var name not '{tokens[n-1][0]}'")
                sys.exit(1)
            if im[0] == "NUMBER":
                result += f"""
    lea rdi, {variables[var][0]}
    xor al, al
    mov rcx, {variables[var][1]}
    cld
    rep stosb
    mov rax, {im[1]}
    mov qword [{variables[var][0]}], rax
"""
            elif im[0] == "STRING":
                val = im[1][1:-1]
                result += f"""
    lea rdi, {variables[var][0]}
    xor al, al
    mov rcx, {variables[var][1]}
    cld
    rep stosb
"""
                for i in range(len(val)):
                    result += f"""
    mov byte [{variables[var][0]} + {i}], {ord(val[i])}"""
            if var == "return":
                result += "\nret\n"
        elif kind == "STRUCT":
            name = tokens[n+1][1]
            strucs[name] = {"items":[], "size":0}
        elif kind == "LPARAM":
            v1 = tokens[n+1][1]
            o = tokens[n+2][1]
            v2 = tokens[n+3][1]
            test = tokens[n+4]
            if not test[0] == "RPARAM":
                print("LPARAM expects RPARAM")
                sys.exit(1)
            var1 = var2 = 0
            if tokens[n+1][0] == "STRING":
                var1 = f'"{v1[1:-1]}"'
            elif tokens[n+1][0] == "NUMBER":
                var1 = f'{v1}'
            elif v1 in variables:
                var1 = f"[{variables[v1][0]}]"
            
            if tokens[n+3][0] == "STRING":
                var2 = f'"{v2[1:-1]}"'
            elif tokens[n+3][0] == "NUMBER":
                var2 = f'{v2}'
            elif v2 in variables:
                var2 = f"[{variables[v2][0]}]"
            ops = {
                "+":"add",
                "-":"sub",
                "*":"imul",
                "/":"idiv",
                "==": "jne",
                "!=": "je",
                ">": "jle",
                "<": "jge",
                ">=": "jl",
                "<=": "jg",
                "%":"mod"
            }
            op = ops[o]
            if op in ["add", "sub"]:
                result += f"""
    mov rax, {var1}
    mov rbx, {var2}
    {op} rax, rbx
"""
            elif op == "imul":
                result += f"""
    mov rax, {var1}
    mov rbx, {var2}
    imul rax, rbx
"""
            elif op == "idiv":
                result += f"""
    xor rdx, rdx
    mov rax, {var1}
    mov rbx, {var2}
    idiv rbx
"""
            elif op == "mod":
                result += f"""
    xor rdx, rdx
    mov rax, {var1}
    mov rbx, {var2}
    idiv rbx
    mov rax, rdx
"""
            else:
                result += f"""
    mov rax, {var1}
    mov rbx, {var2}
    cmp rax, rbx
"""
                ccond = op
        elif kind == "MOVETAL":
            im = tokens[n+1]
            if im[0] == "NUMBER":
                result += f"""
    mov qword [rax], {im[1]}
"""
            elif im[0] == "STRING":
                val = im[1]
                result += f"""
    mov rbx, rax
    mov rdi, rbx
    xor al, al
    mov rcx, 8
    cld
    rep stosb
"""
                for i in range(len(val[1:-1])):
                    result += f"""
    mov rax, rbx
    mov byte [rax + {i}], {ord(val[1:-1][i])}"""
        elif kind == "SIZE":
            m = strucs.get(tokens[n+1][1], None)
            name = tokens[n+1][1]
            if not m:
                print(f"No structure named '{tokens[n+1][1]}'")
                sys.exit(1)
            variables[f"{name}.size"] = [f"{name}_size", 8]
            initdata += f"""
    {name}_size dq {m["size"]}
"""
            
        elif kind == "PARAM":
            name = tokens[n+1][1]
            if tokens[n+1][0] != "IDENT":
                print("Unknown name type")
                sys.exit(1)
            if name in subs:
                vname = tokens[n-1][1]
                size = tokens[n+2][1]
                pnum = subs[name]["lp"]
                subs[name]["params"][int(pnum)] = (f"{name}__$$__{vname}", int(size))
                variables[f"{name}.{vname}"] = [f"{name}__$$__{vname}", int(size)]
                vardata += f"""
    {name}__$$__{vname} resb {size}
"""
                subs[name]["lp"] += 1
            elif name in strucs:
                print("strucdef")
                vname = tokens[n-1][1]
                if not (vname in subs):
                    size = tokens[n+2][1]
                    strucs[name]["items"].append([vname, strucs[name]["size"], size])
                    variables[f"{name}.{vname}"] = [f"{name}_{vname}", 8]
                    initdata += f"""
    {name}_{vname} dq {strucs[name]["size"]}
"""
                    strucs[name]["size"] += int(size)
                elif (vname in subs):
                    size = 8
                    strucs[name]["items"].append([vname, strucs[name]["size"], size])
                    initdata += f"""
    {name}_{vname} dq {vname}_s
"""
                    variables[f"{name}.{vname}"] = [f"{name}_{vname}", 8]
                    strucs[name]["size"] += int(size)
        elif kind == 'VOLAT':
            name = tokens[n+1]
            if name[0] != "IDENT":
                print(f"Unknown variable name type '{name[0]}'")
                sys.exit(1)
            variables[name[1]] = [f"temp+{lv*8}", 8]
            lds2[name[1]] = lv
            lv += 1
            print("v", lv)
        elif value in strucs:
            if not (tokens[n-1][0] in ["PARAM", "STRUCT", "SIZE"]):
                vname = tokens[n+1][1]
                if tokens[n+1][0] != "IDENT":
                    print(f"Unknown name type '{tokens[n+1][0]}' {vname}")
                    sys.exit(1)
                if vname in variables:
                    print(f"Variable or StructInst '{vname}' already exists.")
                    sys.exit(1)
                vardata += f"""
    struc_{vname} resq {strucs[value]["size"]}
"""
                variables[vname] = [f"struc_{vname}", int(strucs[value]["size"])]
                for item in strucs[value]["items"]:
                    variables[f"{vname}.{item[0]}"] = [f"struc_{vname}+{item[1]}", int(item[2])]
        elif kind == "VAR":
            name = tokens[n+1][1]
            elems = tokens[n+2][1]
            if tokens[n+1][0] != "IDENT":
                print(f"Unknown name type '{tokens[n+1][0]}' {name}")
                sys.exit(1)
            if name in variables:
                print(f"Variable '{name}' already exists.")
                sys.exit(1)
            vardata += f"\n    {name}_v resb {elems}"
            variables[name] = [f"{name}_v", int(elems)]
        elif value in subs:
            if not (tokens[n-1][0] in ["PARAM", "GT"] or tokens[n+1][0] in ["RPMOVE", "PARAM"]):
                m = 0
                for param in subs[value]["params"]:
                    v = 0
                    m += 1
                    iv = 0
                    if tokens[n+m][0] == "STRING":
                        v = f'{tokens[n+m][1][1:-1]}'
                        iv = 1
                    elif tokens[n+m][0] == "NUMBER":
                        v = tokens[n+m][1]
                    elif tokens[n+m][1] in variables:
                        v = tokens[n+m][1]
                        v = f"[{variables[v][0]}]"
                        iv = 2
                    if not tokens[n+m][0] in ["IDENT", "NUMBER", "STRING"]:
                        if param[0] != "garb":
                            print(f"{value}{":"}error{":"}Too less parameters")
                            sys.exit(1)
                        break
                    if param[0] == "garb":
                        print(f"{value}{":"}warning{":"} was given more parameters than needed.")
                        break
                    result += f"""
    lea rdi, [{param[0]}]
    xor al, al
    mov rcx, {param[1]}
    cld
    rep stosb
"""
                    if iv == 0:
                        result += f"""
    mov qword [{param[0]}], 0
    mov rax, {v}
    mov qword [{param[0]}], rax
"""
                    elif iv == 2:
                        result += f"""
    lea rsi, {v}
    lea rdi, [{param[0]}]
    mov rcx, {param[1]}
    rep movsb
"""
                    elif iv == 1:
                        for i in range(len(str(v))):
                            result += f"""
    mov byte [{param[0]}+{i}], {ord(str(v)[i])}"""
                result += f"""
    call {value}_s
"""
        elif kind == "ANON":
            name = tokens[n-1][1]
            if tokens[n-1][0] != "IDENT":
                print(f"Unknown name type '{tokens[n-1][0]}' {name}")
                sys.exit(1)
            if name == "loop":
                result += f"\nloopback{wno+1}:\n"
                wnol[cw] = wno # Store which wno this loop is using
                cw += 1
                wno += 1
        elif value == "len":
            var = tokens[n+1]
            if var[0] != "IDENT":
                print(f"Unknown name type '{tokens[n+1][0]}' {var[1]}")
                sys.exit(1)
            var = variables[var[1]]
            result += f"""
    lea rax, {var[0]}
    mov rbx, {var[1]}
    call _strlen_safe
"""
        elif kind == "GT":
            # Peek back to see if this is a named block or just a loop
            if n >= 1:
                if not tokens[n-1][1] == "end":
                    name = tokens[n+1][1]
                    result += f"{name}_s:\n"
                    subs[name] = {"params":[("garb", 8) for _ in range(10)], "lp":0}
            else:
                name = tokens[n+1][1]
                result += f"{name}_s:\n"
                subs[name] = {"params":["garb" for _ in range(10)], "lp":0}
        elif value == "unsafe":
            result += f"\n    {tokens[n+1][1][1:-1]}\n"
        elif kind == "PMOVE":
            var1 = variables[tokens[n-1][1]]
            result += f"""
    lea rax, [{var1[0]}]
"""
        '''elif kind == "LT":
            result += "ret\n"'''
        n += 1
    fresult = f"""{strucdefs}
section .bss
    stdout resb 512
    return_v resb 512
    endl resq 1
    zero_v resb 1
    input_buf resb 512
    uva resb 512
    uvb resb 512
    uvc resb 512
    uvd resb 512
    garb resq 1
{vardata}
    temp resb 1024
section .data
{initdata}

section .text
global _start
output:
    mov rax, 1
    mov rdi, 1
    mov rsi, stdout
    mov rdx, 512
    syscall
    lea rdi, [stdout]
    xor al, al
    mov rcx, 512
    cld
    rep stosb
    ret

clean_regs:
    xor rax, rax
    mov rbx, rax
    mov rcx, rax
    mov rdx, rax
    ret

; Input:  RAX = pointer to the string
; Output: RAX = length of the string
; Modifies: RBX (counter), RAX (result), RDI (temp pointer)

; Input:   RAX = pointer to the string
;          RBX = fallback/buffer size (the limit)
; Output:  RAX = actual length found (number of non-null bytes)
; Modifies: RCX (counter), RDI (moving pointer), RAX (result)

_strlen_safe:
    mov rdi, rax        ; Copy start pointer to RDI
    xor rcx, rcx        ; RCX will be our counter (start at 0)

.loop:
    cmp rcx, rbx        ; Have we reached the fallback limit?
    je .done            ; If RCX == RBX, stop searching
    
    cmp byte [rdi], 0   ; Is the current byte a null terminator?
    je .done            ; If yes, stop searching
    
    inc rcx             ; Increment counter
    inc rdi             ; Move to next byte
    jmp .loop           ; Repeat

.done:
    mov rax, rcx        ; Return the final count in RAX
    ret

input_to_int:
    ; --- Step 1: Read from Stdin ---
    mov rax, 0              ; sys_read
    mov rdi, 0              ; stdin
    mov rsi, input_buf      ; buffer
    mov rdx, 512            ; max bytes
    syscall

    ; --- Step 2: Prepare for Conversion ---
    lea rsi, [input_buf]    ; Pointer to string
    xor rax, rax            ; Clear RAX (this will hold our result)
    xor rcx, rcx            ; Clear RCX (for character processing)

.convert_loop:
    movzx rcx, byte [rsi]   ; Get the current character
    
    ; Check for end of input (newline or null)
    cmp cl, 10              ; Check for '\\n'
    je .done
    cmp cl, 0               ; Check for null
    je .done
    
    ; Validate: Ensure character is between '0' and '9'
    cmp cl, '0'
    jl .done                ; If less than '0', stop
    cmp cl, '9'
    jg .done                ; If greater than '9', stop

    ; --- Step 3: The Math (Result = Result * 10 + (char - '0')) ---
    sub cl, '0'             ; Convert ASCII to digit (e.g., '5' becomes 5)
    imul rax, 10            ; Multiply current total by 10
    add rax, rcx            ; Add the new digit
    
    inc rsi                 ; Move to next character in buffer
    jmp .convert_loop

.done:
    ; RAX now contains the 64-bit integer
    ; We clear the other registers to match your semicolon logic
    mov rbx, rax
    lea rdi, [input_buf]
    xor al, al
    mov rcx, 512
    cld
    rep stosb
    mov qword [input_buf], rbx
    lea rax, [input_buf]
    xor rbx, rbx
    xor rcx, rcx
    xor rdx, rdx
    ret

int_to_ascii:
    ; Input: RAX contains the integer
    ; Output: ASCII string written to [stdout]
    
    lea rdi, [stdout]       ; Point RDI to your buffer
    add rdi, 20             ; Start at the end of a 20-byte temp space
    mov byte [rdi], 0       ; Null terminator for safety
    mov rbx, 10             ; Divisor
    
.convert_loop_pint:
    xor rdx, rdx            ; CRITICAL: Clear RDX for division
    div rbx                 ; RAX / 10. Remainder (digit) goes to RDX
    add dl, '0'             ; Convert digit to ASCII
    dec rdi                 ; Move buffer pointer backwards
    mov [rdi], dl           ; Store the character
    
    test rax, rax           ; Is the quotient 0?
    jnz .convert_loop_pint       ; If not, keep dividing

    ; --- Now move the result to the START of stdout ---
    ; RDI currently points to the first digit. 
    ; We need to shift it so it starts at stdout[0]
    lea rsi, [rdi]          ; Source: where the string actually started
    lea rdi, [stdout]       ; Destination: the very beginning
    
.copy_loop:
    mov al, [rsi]
    mov [rdi], al
    mov byte [rsi], 0  ; <--- ADD THIS: Zero out the "ghost" digit after copying
    inc rsi
    inc rdi
    cmp al, 0
    jne .copy_loop

    ; --- Cleanup to match Symtran's Semicolon Logic ---
    xor rax, rax
    xor rbx, rbx
    xor rcx, rcx
    xor rdx, rdx
    ret

get_raw_input:
    ; --- Step 1: Syscall to Read ---
    mov rax, 0              ; sys_read
    mov rdi, 0              ; stdin
    mov rsi, input_buf      ; Destination buffer
    mov rdx, 512            ; Max bytes to read
    syscall                 ; Returns number of bytes read in RAX

    ; --- Step 2: Strip Newline ---
    ; RAX contains the number of bytes read (including \\n)
    test rax, rax           ; Did we read 0 bytes?
    jz .done                ; If so, skip trimming

    lea rsi, [input_buf]    ; Pointer to start
    add rsi, rax            ; Move to the end of the input
    dec rsi                 ; Move back one (to the last character)

    cmp byte [rsi], 10      ; Is it a newline (0x0A)?
    jne .done               ; If not, don't strip
    mov byte [rsi], 0       ; Replace \\n with null terminator

.done:
    lea rax, [input_buf]    ; Load the ADDRESS of the buffer into RAX
    ret

{result}
_start:
    xor rax, rax
    mov rax, 10
    mov qword [endl], rax
    call main_s
    xor rdi, rdi
    mov rax, 60
    syscall
"""
    return fresult

file = sys.argv[1]
ofile = sys.argv[2]
res = parse(file)
open(".output.asm", 'w').write(res)
os.system(f"""
nasm -f elf64 .output.asm -o .output.o && ld .output.o -o {ofile}
""")