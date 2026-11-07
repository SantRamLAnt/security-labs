# A small typed language: interpreter and type checker

`tiny_lang.py` builds the languages from KAIST's *Programming Languages I and II* in Python (the
course uses Scala): arithmetic with identifiers, first-class functions with closures, recursion,
and a type checker for numbers, booleans and function types.

Programs are s-expressions, for example `(letrec sum (n num) num (if (<= n 0) 0 (+ n (sum (- n 1)))) (sum 100))`,
which type-checks as `num` and returns 5050.

What it shows:

- **Static scope.** `(let y 1 (let f (fun (x num) (+ x y)) (let y 100 (f 10))))` gives 11,
  because f sees the y where it was written. Run with dynamic scope, the same program gives 110.
- **Type errors caught before running.** Adding a boolean, an `if` on a number, calling a number,
  branches of different types, and the wrong argument type are all rejected with a message.
- **Soundness, tested.** Out of 3,000 random programs, the checker accepted 799, and none of them
  hit a type error when run. Of the 2,201 it rejected, 2,142 do crash if you run them anyway. The
  other 59 happen to avoid the bad branch, which is the price of checking before running.
- **A Lab J style rule.** Section loading as a percent of the device rating, the same calculation
  Lab J's `topology.py` reports, written in the language: 430 A on a 600 A device is 71%, not
  overloaded.

`python3 tiny_lang.py --check` runs it with checks. Built with an AI coding assistant, like the
rest of this repository.
