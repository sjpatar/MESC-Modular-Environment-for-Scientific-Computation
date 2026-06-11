from typing import List
from .tokenizer import Token
from .ast_nodes import (
    Node, Program, Assign, MultiAssign, BinOp, UnaryOp, Number, String,
    Variable, Call, Index, Member, Matrix, CellArray, Range, Command,
    IfBlock, ForLoop, WhileLoop, Break, Continue, GlobalDecl,
    FunctionDef, Return, AnonymousFunc, TryBlock, SwitchBlock, ClassDef
)
from .locale import tr

# ==========================================================
# PARSER IMPLEMENTATION
# ==========================================================
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ---------------- Token helpers ----------------
    def curr(self) -> Token:
        return self.tokens[self.pos]

    def consume(self, type_name=None, value=None):
        t = self.curr()
        if type_name and t.type != type_name:
            raise SyntaxError(
                tr("err_expected_type", expected=type_name, got=t.type, value=t.value)
            )
        if value and t.value != value:
            raise SyntaxError(tr("err_expected_value", expected=value, got=t.value))
        self.pos += 1
        return t

    def lookahead(self, n=1) -> Token:
        p = self.pos + n
        return self.tokens[p] if p < len(self.tokens) else Token('EOF', '')

    def match(self, value) -> bool:
        if self.curr().value == value:
            self.consume()
            return True
        return False

    # ---------------- Program ----------------
    def parse(self) -> Program:
        stmts = []
        while self.curr().type != 'EOF':
            if self.curr().type in ('NEWLINE', ';'):
                self.consume()
                continue
            stmts.append(self.statement())
        return Program(stmts)

    # ---------------- Statement ----------------
    def statement(self) -> Node:
        t = self.curr()

        # 1. Keywords
        if t.type == 'KEYWORD':
            if t.value == 'classdef': return self.parse_classdef()
            if t.value == 'function': return self.parse_function()
            if t.value == 'if': return self.parse_if()
            if t.value == 'switch': return self.parse_switch()
            if t.value == 'try': return self.parse_try()
            if t.value == 'for': return self.parse_for()
            if t.value == 'while': return self.parse_while()
            if t.value == 'break': self.consume(); return Break()
            if t.value == 'continue': self.consume(); return Continue()
            if t.value == 'global': return self.parse_global()
            if t.value == 'return':
                self.consume()
                if self.curr().type not in ('NEWLINE',';','EOF'):
                    return Return(self.expression())
                return Return(None)
        
        # 2. Command Syntax: "hold on", "grid off"
        if (t.type=='ID' and 
            self.lookahead().type in ('ID','STRING','NUMBER') and 
            self.lookahead().value not in ('(', '.', '=', ',', ';', '+', '-', '*', '/', '^', '[', '{') 
            ): 
            return self.parse_command()

        # 3. Expression or Assignment
        expr = self.expression()

        # Check for Assignment '='
        if self.curr().value == '=':
            self.consume(value='=')
            rhs = self.expression()

            if isinstance(expr, Variable):
                return Assign(expr.name, rhs)
            
            elif isinstance(expr, Matrix):
                targets = []
                for row in expr.rows:
                    for item in row:
                        if isinstance(item, Variable):
                            targets.append(item.name)
                        else:
                            raise SyntaxError(tr("err_invalid_lhs"))
                return MultiAssign(targets, rhs)

            # Support s.field = 5
            elif isinstance(expr, Member):
                return Assign(expr, rhs)

            # Support Indexed Assignment A(1) = 5
            elif isinstance(expr, Call):
                 return Assign(expr, rhs)
                 
            # [FIX] Added catch-all to prevent silent assignment failures
            else:
                raise SyntaxError(tr("err_invalid_lhs"))

        return expr

    # ---------------- Function ----------------
    def parse_function(self) -> FunctionDef:
        self.consume('KEYWORD','function')

        outputs = []
        
        # Case 1: function [y1, y2] = f(x)
        if self.curr().type == '[':
            self.consume('[')
            while self.curr().type == 'ID':
                outputs.append(self.consume().value)
                if self.curr().value == ',':
                    self.consume(',')
            self.consume(']')
            self.consume(value='=')

        # Case 2: function y = f(x)
        elif self.curr().type == 'ID' and self.lookahead().value == '=':
             outputs.append(self.consume('ID').value)
             self.consume(value='=')

        # Case 3: function f(x) (No outputs)
        
        name = self.consume('ID').value

        args = []
        # [FIX] Make parentheses optional to maintain strict MATLAB/Octave parity
        if self.curr().value == '(':
            self.consume('(')
            if self.curr().type == 'ID':
                args.append(self.consume('ID').value)
                while self.curr().value == ',':
                    self.consume(',')
                    args.append(self.consume('ID').value)
            self.consume(')')

        body = self.parse_block()
        self.consume('KEYWORD','end')
        return FunctionDef(name, args, outputs, body)

    # ---------------- Block ----------------
    def parse_block(self) -> List[Node]:
        body = []
        while self.curr().type != 'EOF' and not (
            self.curr().type == 'KEYWORD' and self.curr().value in ('end','else','elseif','catch','case','otherwise')
        ):
            if self.curr().type in ('NEWLINE',';'):
                self.consume()
                continue
            body.append(self.statement())
        return body

    # ---------------- Control Flow ----------------
    def parse_if(self) -> IfBlock:
        self.consume('KEYWORD','if')
        cond = self.expression()
        body = self.parse_block()

        conditions = [(cond, body)]
        else_body = None

        while self.curr().type == 'KEYWORD' and self.curr().value == 'elseif':
            self.consume()
            cond = self.expression()
            conditions.append((cond, self.parse_block()))

        if self.curr().type == 'KEYWORD' and self.curr().value == 'else':
            self.consume()
            else_body = self.parse_block()

        self.consume('KEYWORD','end')
        return IfBlock(conditions, else_body)
    
    def parse_try(self) -> TryBlock:
        self.consume('KEYWORD', 'try')
        try_body = self.parse_block()
        
        catch_var = None
        catch_body = []
        
        if self.curr().type == 'KEYWORD' and self.curr().value == 'catch':
            self.consume()
            # Optional capture: catch ME
            if self.curr().type == 'ID':
                catch_var = self.consume('ID').value
            
            catch_body = self.parse_block()
            
        self.consume('KEYWORD', 'end')
        return TryBlock(try_body, catch_var, catch_body)

    def parse_switch(self) -> SwitchBlock:
        self.consume('KEYWORD', 'switch')
        expr = self.expression()
        
        cases = []
        otherwise_body = None
        
        # Skip optional newlines after switch expression
        while self.curr().type in ('NEWLINE', ';'):
            self.consume()
            
        while self.curr().type == 'KEYWORD' and self.curr().value == 'case':
            self.consume()
            case_val = self.expression()
            # Handle potential comma/newline after case value
            if self.curr().type in ('NEWLINE', ';', ','):
                self.consume()
            
            body = self.parse_block()
            cases.append((case_val, body))
            
        if self.curr().type == 'KEYWORD' and self.curr().value == 'otherwise':
            self.consume()
            otherwise_body = self.parse_block()
            
        self.consume('KEYWORD', 'end')
        return SwitchBlock(expr, cases, otherwise_body)

    # ---------------- Loops / Globals ----------------
    def parse_for(self) -> ForLoop:
        self.consume('KEYWORD','for')
        var = self.consume('ID').value
        self.consume(value='=')
        rng = self.expression()
        body = self.parse_block()
        self.consume('KEYWORD','end')
        return ForLoop(var, rng, body)

    def parse_while(self) -> WhileLoop:
        self.consume('KEYWORD','while')
        cond = self.expression()
        body = self.parse_block()
        self.consume('KEYWORD','end')
        return WhileLoop(cond, body)

    def parse_global(self) -> GlobalDecl:
        self.consume('KEYWORD','global')
        names = []
        while self.curr().type == 'ID':
            names.append(self.consume().value)
            # [FIX] Safely handle comma-separated variables in global declarations
            if self.curr().value == ',':
                self.consume()
        return GlobalDecl(names)

    def parse_command(self) -> Command:
        cmd = self.consume('ID').value
        args = []
        while self.curr().type in ('ID','STRING','NUMBER'):
            args.append(self.consume().value)
        return Command(cmd, args)

    # ---------------- Expressions ----------------
    def expression(self) -> Node:
        # Start at the lowest precedence (Logical OR)
        return self.logic_or()

    def logic_or(self) -> Node:
        node = self.logic_and()
        while self.curr().type == 'OP' and self.curr().value in ('|', '||'):
            op = self.consume().value
            node = BinOp(node, op, self.logic_and())
        return node

    def logic_and(self) -> Node:
        node = self.relational()
        while self.curr().type == 'OP' and self.curr().value in ('&', '&&'):
            op = self.consume().value
            node = BinOp(node, op, self.relational())
        return node

    def relational(self) -> Node:
        node = self.range_expr()
        # Handle ==, ~=, <, >, <=, >=
        while self.curr().type == 'OP' and self.curr().value in ('==', '~=', '<', '>', '<=', '>='):
            op = self.consume().value
            node = BinOp(node, op, self.range_expr())
        return node

    def range_expr(self) -> Node:
        node = self.term()
        if self.curr().value == ':':
            self.consume()
            end = self.term()
            if self.curr().value == ':':
                self.consume()
                step = end
                end = self.term()
                return Range(node, step, end)
            return Range(node, None, end)
        return node

    def term(self) -> Node:
        node = self.factor()
        while self.curr().value in ('+','-'):
            op = self.consume().value
            node = BinOp(node, op, self.factor())
        return node

    def factor(self) -> Node:
        node = self.power()
        while self.curr().value in ('*','/','\\','.*','./','.\\'):
            op = self.consume().value
            node = BinOp(node, op, self.power())
        return node

    def power(self) -> Node:
        node = self.atom()
        while self.curr().value in ('^','.^'):
            op = self.consume().value
            node = BinOp(node, op, self.atom())
        return node

    # ---------------- Atom ----------------
    def atom(self) -> Node:
        t = self.curr()

        # 1. Unary Operators
        if t.value == '-': self.consume(); return UnaryOp('-', self.atom())
        if t.value == '~': self.consume(); return UnaryOp('~', self.atom())

        # [FIX] Handle 'end' as a String node instead of a Variable
        if t.type == 'KEYWORD' and t.value == 'end':
            self.consume()
            return String('end')

        # 2. Base Nodes
        node = None
        if t.type == 'AT':
            self.consume('AT')
            
            # [FIX] Handle function handles: @funcName
            if self.curr().type == 'ID':
                name = self.consume('ID').value
                node = Variable(name)
            
            # Handle anonymous functions: @(args) ...
            elif self.curr().value == '(':
                args = []
                self.consume('(')
                if self.curr().type == 'ID':
                    args.append(self.consume('ID').value)
                    while self.curr().value == ',':
                        self.consume(',')
                        args.append(self.consume('ID').value)
                self.consume(')')
                node = AnonymousFunc(args, self.expression())
            
            else:
                raise SyntaxError(tr("err_expected_identifier_after_at"))

        elif t.type == 'NUMBER': self.consume(); node = Number(t.value)
        elif t.type == 'STRING': self.consume(); node = String(t.value)

        elif t.type == 'ID':
            node = Variable(self.consume().value)
            
        elif t.type == '[': node = self.parse_matrix()
        elif t.type == '{': node = self.parse_cell()

        elif t.value == '(':
            self.consume()
            node = self.expression()
            self.consume(')')
            
        elif t.value == ':':
            self.consume()
            node = String(':') 
        
        else:
            raise SyntaxError(tr("err_unexpected_token", type=t.type, value=t.value))

        # 3. Trailers: .field, (args), {args}, ' (transpose)
        while True:
            if self.curr().value == '.':
                self.consume('.')
                field = self.consume('ID').value
                node = Member(node, field)
            elif self.curr().value == '(':
                node = self.parse_call_args(node)
            
            elif self.curr().type == 'OP' and self.curr().value == "'":
                self.consume()
                node = Member(node, 'H') # Conjugate Transpose
            
            elif self.curr().type == 'OP' and self.curr().value == ".'":
                self.consume()
                node = Member(node, 'T') # Array Transpose

            else:
                break
        
        return node

    def parse_call_args(self, target: Node) -> Node:
        self.consume('(')
        args = []

        if self.curr().value != ')':
            args.append(self.expression())
            while self.curr().value == ',':
                self.consume(',')
                args.append(self.expression())

        self.consume(')')
        
        return Call(target if isinstance(target, (str, Variable, Member)) else target, args)


    # ---------------- Matrix / Cell ----------------
    def parse_matrix(self) -> Matrix:
        self.consume('[')
        rows = []
        row = []
        while self.curr().type != ']':
            if self.curr().type in ('NEWLINE',';'):
                if row:
                    rows.append(row); row=[]
                self.consume(); continue
            if self.curr().value == ',':
                self.consume(); continue
            row.append(self.expression())
        if row: rows.append(row)
        self.consume(']')
        return Matrix(rows)

    def parse_cell(self) -> CellArray:
        self.consume('{')
        rows = []; row=[]
        while self.curr().type != '}':
            if self.curr().type in ('NEWLINE',';'):
                if row: rows.append(row); row=[]
                self.consume(); continue
            if self.curr().value == ',':
                self.consume(); continue
            row.append(self.expression())
        if row: rows.append(row)
        self.consume('}')
        return CellArray(rows)
    
    # ---------------- OOP / Classes ----------------
    def parse_classdef(self) -> ClassDef:
        self.consume('KEYWORD', 'classdef')
        name = self.consume('ID').value
        
        properties = []
        methods = []
        
        # Loop until the class 'end'
        while self.curr().type != 'EOF' and not (
            self.curr().type == 'KEYWORD' and self.curr().value == 'end'
        ):
            # Skip newlines/semicolons
            if self.curr().type in ('NEWLINE', ';'):
                self.consume()
                continue
            
            # Check for blocks
            if self.curr().type == 'KEYWORD':
                if self.curr().value == 'properties':
                    properties.extend(self.parse_properties())
                elif self.curr().value == 'methods':
                    methods.extend(self.parse_methods())
                else:
                    # Likely an event or attribute we don't support yet, consume to avoid loop
                    self.consume()
            else:
                self.consume()

        self.consume('KEYWORD', 'end')
        return ClassDef(name, properties, methods)

    def parse_properties(self):
        self.consume('KEYWORD', 'properties')
        props = []
        while self.curr().value != 'end' and self.curr().type != 'EOF':
            if self.curr().type == 'ID':
                props.append(self.consume('ID').value)
                # Handle optional default value: Prop = 10
                if self.curr().value == '=':
                    self.consume('=')
                    self.expression() # Consume logic but ignore for now (Step 1)
            
            elif self.curr().type in ('NEWLINE', ';', ','):
                self.consume()
            else:
                # Unexpected token inside properties block, break to avoid inf loop
                if self.curr().value == 'methods': break 
                self.consume()
                
        self.consume('KEYWORD', 'end')
        return props

    def parse_methods(self):
        self.consume('KEYWORD', 'methods')
        funcs = []
        while self.curr().value != 'end' and self.curr().type != 'EOF':
            if self.curr().type == 'KEYWORD' and self.curr().value == 'function':
                funcs.append(self.parse_function())
            elif self.curr().type in ('NEWLINE', ';'):
                self.consume()
            else:
                # Unexpected token
                if self.curr().value == 'properties': break
                self.consume()
        self.consume('KEYWORD', 'end')
        return funcs