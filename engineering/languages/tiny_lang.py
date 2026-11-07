#!/usr/bin/env python3
"""A small typed functional language: an interpreter and a type checker.

Course material this follows (KAIST, Programming Languages I and II; the course builds these in
Scala, this is the same structure in Python):
  PL I  module 1  syntax and semantics, pattern matching on the syntax tree
        module 2  identifiers (let), the VAE language
        module 3  first-class functions, closures, static vs dynamic scope (FVAE)
        module 4  recursion (RFAE)
  PL II module 3  types and type rules, a type checker (TFAE)
        module 4  type checking a language with recursion (TRFAE)

Programs are written as s-expressions so the parser stays a few lines:
  numbers, true, false, identifiers
  (+ a b) (- a b) (* a b) (<= a b) (if c then else)
  (let x e body)                      bind x to e inside body
  (fun (x T) body)                    a function of one argument of type T
  (f arg)                             apply a function
  (letrec f (x T) R body rest)        a recursive function from T to R, in scope in rest
Types: num, bool, and (-> A B) for functions.

What the script checks:
  - arithmetic, let, shadowing, closures, recursion (sum 1..100, 10 factorial)
  - static scope: a function sees the variables where it was written, not where it was called.
    The same program run with dynamic scope gives a different answer.
  - the type checker rejects bad programs before they run (adding a boolean, an if on a number,
    calling a number, branches of different types)
  - type soundness, tested: 3,000 random programs are generated; every one the checker accepts
    runs without a type error at run time
  - a rule in the style of Lab J (section loading as a percent of the device rating) written in
    the language, type-checked and run

Usage: tiny_lang.py [--check]
"""
import random
import sys

# ---------------- parsing ----------------

def tokenize(src):
    return src.replace("(", " ( ").replace(")", " ) ").split()


def parse(src):
    toks = tokenize(src)

    def read(i):
        if toks[i] == "(":
            out, i = [], i + 1
            while toks[i] != ")":
                node, i = read(i)
                out.append(node)
            return out, i + 1
        t = toks[i]
        if t.lstrip("-").isdigit():
            return int(t), i + 1
        return t, i + 1

    node, i = read(0)
    if i != len(toks):
        raise SyntaxError("extra tokens")
    return node


def parse_type(t):
    if t in ("num", "bool"):
        return t
    if isinstance(t, list) and len(t) == 3 and t[0] == "->":
        return ("->", parse_type(t[1]), parse_type(t[2]))
    raise SyntaxError(f"bad type {t}")


# ---------------- interpreter ----------------

class RunTimeTypeError(Exception):
    pass


class Closure:
    def __init__(self, param, body, env):
        self.param, self.body, self.env = param, body, env


def num(v):
    if isinstance(v, bool) or not isinstance(v, int):
        raise RunTimeTypeError(f"expected a number, got {v!r}")
    return v


def evaluate(e, env, dynamic=False):
    """Environment-passing interpreter. env is a dict chain; closures capture it (static scope)."""
    if isinstance(e, int):
        return e
    if e == "true":
        return True
    if e == "false":
        return False
    if isinstance(e, str):
        if e not in env:
            raise NameError(f"free identifier {e}")
        return env[e]
    op = e[0]
    if op in ("+", "-", "*", "<="):
        a, b = num(evaluate(e[1], env, dynamic)), num(evaluate(e[2], env, dynamic))
        return {"+": a + b, "-": a - b, "*": a * b, "<=": a <= b}[op]
    if op == "if":
        c = evaluate(e[1], env, dynamic)
        if not isinstance(c, bool):
            raise RunTimeTypeError(f"if needs a boolean, got {c!r}")
        return evaluate(e[2] if c else e[3], env, dynamic)
    if op == "let":
        return evaluate(e[3], {**env, e[1]: evaluate(e[2], env, dynamic)}, dynamic)
    if op == "fun":
        return Closure(e[1][0], e[2], env)
    if op == "letrec":
        _, f, (x, _), _, body, rest = e
        rec_env = dict(env)
        clo = Closure(x, body, rec_env)
        rec_env[f] = clo                       # the closure's own environment contains itself
        return evaluate(rest, {**env, f: clo}, dynamic)
    # application
    f = evaluate(e[0], env, dynamic)
    arg = evaluate(e[1], env, dynamic)
    if not isinstance(f, Closure):
        raise RunTimeTypeError(f"cannot call {f!r}")
    base = {**f.env, **env} if dynamic else f.env   # dynamic scope: the caller's variables win
    return evaluate(f.body, {**base, f.param: arg}, dynamic)


def run(src, dynamic=False):
    return evaluate(parse(src), {}, dynamic)


# ---------------- type checker ----------------

class TypeError_(Exception):
    pass


def typeof(e, tenv):
    if isinstance(e, int):
        return "num"
    if e in ("true", "false"):
        return "bool"
    if isinstance(e, str):
        if e not in tenv:
            raise TypeError_(f"free identifier {e}")
        return tenv[e]
    op = e[0]
    if op in ("+", "-", "*", "<="):
        for side in e[1:]:
            if typeof(side, tenv) != "num":
                raise TypeError_(f"{op} needs numbers")
        return "bool" if op == "<=" else "num"
    if op == "if":
        if typeof(e[1], tenv) != "bool":
            raise TypeError_("if condition must be bool")
        a, b = typeof(e[2], tenv), typeof(e[3], tenv)
        if a != b:
            raise TypeError_(f"if branches differ: {a} vs {b}")
        return a
    if op == "let":
        return typeof(e[3], {**tenv, e[1]: typeof(e[2], tenv)})
    if op == "fun":
        (x, t), body = e[1], e[2]
        T = parse_type(t)
        return ("->", T, typeof(body, {**tenv, x: T}))
    if op == "letrec":
        _, f, (x, t), r, body, rest = e
        T, R = parse_type(t), parse_type(r)
        ft = ("->", T, R)
        if typeof(body, {**tenv, f: ft, x: T}) != R:
            raise TypeError_(f"{f} does not return {R}")
        return typeof(rest, {**tenv, f: ft})
    ft = typeof(e[0], tenv)
    at = typeof(e[1], tenv)
    if not (isinstance(ft, tuple) and ft[0] == "->"):
        raise TypeError_("calling something that isn't a function")
    if ft[1] != at:
        raise TypeError_(f"argument type {at} doesn't match {ft[1]}")
    return ft[2]


def check(src):
    return typeof(parse(src), {})


def show(t):
    return t if isinstance(t, str) else f"({show(t[1])} -> {show(t[2])})"


# ---------------- random programs for the soundness test ----------------

def random_program(rng, depth=0, names=()):
    leaves = [str(rng.randint(-5, 9)), "true", "false"] + list(names)
    if depth > 3 or rng.random() < 0.25:
        return rng.choice(leaves)
    k = rng.random()
    sub = lambda: random_program(rng, depth + 1, names)
    if k < 0.35:
        return f"({rng.choice(['+', '-', '*', '<='])} {sub()} {sub()})"
    if k < 0.55:
        return f"(if {sub()} {sub()} {sub()})"
    if k < 0.75:
        v = rng.choice("abc")
        return f"(let {v} {sub()} {random_program(rng, depth + 1, names + (v,))})"
    if k < 0.9:
        v = rng.choice("xyz")
        t = rng.choice(["num", "bool"])
        return f"((fun ({v} {t}) {random_program(rng, depth + 1, names + (v,))}) {sub()})"
    return f"({sub()} {sub()})"


# ---------------- examples ----------------

EXAMPLES = [
    ("arithmetic and let", "(let x 7 (let y 5 (* (+ x y) 2)))", 24),
    ("shadowing", "(let x 1 (let x (+ x 10) x))", 11),
    ("closure: make an adder", "(let add (fun (n num) (fun (m num) (+ n m))) ((add 3) 4))", 7),
    ("recursion: sum 1..100",
     "(letrec sum (n num) num (if (<= n 0) 0 (+ n (sum (- n 1)))) (sum 100))", 5050),
    ("recursion: 10 factorial",
     "(letrec fact (n num) num (if (<= n 1) 1 (* n (fact (- n 1)))) (fact 10))", 3628800),
]

SCOPE = "(let y 1 (let f (fun (x num) (+ x y)) (let y 100 (f 10))))"

BAD = [
    ("adding a boolean", "(+ 1 (<= 1 2))"),
    ("if on a number", "(if 1 2 3)"),
    ("calling a number", "(5 3)"),
    ("branches of different types", "(if true 1 false)"),
    ("wrong argument type", "((fun (x num) (+ x 1)) true)"),
]

# Section loading as a percent of rating, as Lab J's topology.py reports it (100 * amps / rating),
# with integer division done by repeated subtraction because the language only has + - *.
LOADING = """
(letrec div (a num) (-> num num) (fun (b num) (if (<= b a) (+ 1 ((div (- a b)) b)) 0))
  (let pct (fun (amps num) (fun (rating num) ((div (* 100 amps)) rating)))
    (let overloaded (fun (amps num) (fun (rating num) (<= 101 ((pct amps) rating))))
      (if ((overloaded 430) 600) 1 0))))
"""
LOADING_PCT = """
(letrec div (a num) (-> num num) (fun (b num) (if (<= b a) (+ 1 ((div (- a b)) b)) 0))
  ((div (* 100 430)) 600))
"""


def main():
    bad_results = []
    print("  Examples (type, then value)")
    for name, src, want in EXAMPLES:
        t, v = check(src), run(src)
        print(f"    {name:<28s} {show(t):<6s} {v}")
        if v != want or t != "num":
            bad_results.append(name)

    st, dy = run(SCOPE), run(SCOPE, dynamic=True)
    print(f"\n  Scope: {SCOPE}")
    print(f"    static scope (what the interpreter does): {st}")
    print(f"    dynamic scope (f sees the caller's y): {dy}")
    if (st, dy) != (11, 110):
        bad_results.append("scope")

    print("\n  Rejected by the type checker before running")
    for name, src in BAD:
        try:
            check(src)
            print(f"    {name:<28s} NOT rejected")
            bad_results.append(name)
        except TypeError_ as err:
            print(f"    {name:<28s} {err}")

    rng = random.Random(20261106)
    accepted = rejected = stuck = rejected_crash = 0
    for _ in range(3000):
        src = random_program(rng)
        try:
            check(src)
        except (TypeError_, NameError):
            rejected += 1
            try:
                run(src)
            except (RunTimeTypeError, NameError):
                rejected_crash += 1
            continue
        accepted += 1
        try:
            run(src)
        except RunTimeTypeError:
            stuck += 1
    print(f"\n  Soundness test: 3,000 random programs, {accepted} accepted by the checker, {rejected} rejected")
    print(f"    accepted programs that hit a type error while running: {stuck}")
    print(f"    rejected programs that crash if run anyway: {rejected_crash} of {rejected}"
          " (the rest happen to dodge the bad branch)")
    if stuck or accepted < 300 or rejected_crash < rejected // 2:
        bad_results.append("soundness")

    print("\n  A Lab J style rule in the language: is 430 A on a 600 A device over 100%?")
    print(f"    type {show(check(LOADING))}; loading {run(LOADING_PCT)}% (integer); overloaded = {run(LOADING)}")
    if run(LOADING_PCT) != 71 or run(LOADING) != 0:
        bad_results.append("loading rule")

    if "--check" in sys.argv:
        print("\n  check:", "PASS" if not bad_results else f"FAIL {bad_results}")
        sys.exit(len(bad_results))


if __name__ == "__main__":
    main()
