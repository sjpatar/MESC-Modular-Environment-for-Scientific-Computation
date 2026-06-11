# mathex/language/ast_nodes.py
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

@dataclass
class Node:
    pass

@dataclass
class Program(Node):
    stmts: List[Node]

@dataclass
class Assign(Node):
    target: Any
    value: Node

@dataclass
class MultiAssign(Node):
    targets: List[str]
    value: Node

@dataclass
class BinOp(Node):
    left: Node
    op: str
    right: Node

@dataclass
class UnaryOp(Node):
    op: str
    operand: Node

@dataclass
class Number(Node):
    value: str

@dataclass
class String(Node):
    value: str

@dataclass
class Variable(Node):
    name: str

@dataclass
class Call(Node):
    func: Any
    args: List[Node]

@dataclass
class Index(Node):
    target: Node
    args: List[Node]

@dataclass
class Member(Node):
    target: Node
    field: str

@dataclass
class Matrix(Node):
    rows: List[List[Node]]

@dataclass
class CellArray(Node):
    rows: List[List[Node]]

@dataclass
class Range(Node):
    start: Node
    step: Optional[Node]
    end: Node

@dataclass
class Command(Node):
    name: str
    args: List[str]

@dataclass
class IfBlock(Node):
    conditions: List[Tuple[Node, List[Node]]]
    else_body: Optional[List[Node]]

@dataclass
class SwitchBlock(Node):
    expression: Node
    cases: List[Tuple[Node, List[Node]]]
    otherwise_body: Optional[List[Node]]

@dataclass
class TryBlock(Node):
    try_body: List[Node]
    catch_var: Optional[str]
    catch_body: List[Node]

@dataclass
class ForLoop(Node):
    var: str
    iterable: Node
    body: List[Node]

@dataclass
class WhileLoop(Node):
    condition: Node
    body: List[Node]

@dataclass
class Break(Node):
    pass

@dataclass
class Continue(Node):
    pass

@dataclass
class Return(Node):
    value: Optional[Node]

@dataclass
class GlobalDecl(Node):
    names: List[str]

@dataclass
class FunctionDef(Node):
    name: str
    args: List[str]
    outputs: List[str]
    body: List[Node]

@dataclass
class AnonymousFunc(Node):
    args: List[str]
    body: Node

@dataclass
class ClassDef(Node):
    name: str
    properties: List[str]
    methods: List[FunctionDef]