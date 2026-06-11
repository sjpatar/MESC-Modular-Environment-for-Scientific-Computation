from .tokenizer import Tokenizer
from .parser import Parser
from .ast_nodes import (
    Program, Assign, BinOp, UnaryOp, Number, Variable, Call,
    Matrix, CellArray, Range, Command, String, Index, Member,
    IfBlock, ForLoop, WhileLoop, Break, Continue, GlobalDecl,
    FunctionDef, Return, AnonymousFunc, MultiAssign, TryBlock, SwitchBlock,
    ClassDef
)

# List of commands that should be auto-called if found as bare variables
AUTO_CALL_COMMANDS = {
    'clc', 'clear', 'clf', 'cla', 'hold', 'grid', 'box',
    'tic', 'toc', 'who', 'whos', 'pwd', 'drawnow', 
    'axis', 'shading', 'lighting', 'view', 'figure', 'shg',
    # --- NEW: Assamese Auto-Call Commands ---
    'মচিদিয়া', 'দেখুওৱা', 'ৰৈযোৱা', 'গ্ৰিড', 'সহায়'
}

class ASTCompiler:
    def __init__(self):
        self.indent_level = 0
        # Maps generated Python line number -> Original MATLAB line number
        self.line_map = {} 
        self.current_py_line = 1

    def indent(self):
        return "    " * self.indent_level

    def _append_stmt(self, lines, stmt):
        """Helper to append a statement with correct indentation handling."""
        generated = self.generate(stmt)
        if not generated.strip():
            return

        # Record Line Mapping
        # If the parser attached a line number, map the current Python block start to it.
        matlab_line = getattr(stmt, 'lineno', None)
        
        for line in generated.split("\n"):
            # Map current Python line to the Node's original line
            if matlab_line is not None:
                self.line_map[self.current_py_line] = matlab_line

            if line.startswith(" "):
                lines.append(line)
            else:
                lines.append(self.indent() + line)
            
            # Increment Python line counter
            self.current_py_line += 1

    # --------------------------------------------------
    def generate(self, node):
        # ---------------- Program ----------------
        if isinstance(node, Program):
            lines = []
            for s in node.stmts:
                self._append_stmt(lines, s)
            return "\n".join(lines)

        # ---------------- ClassDef ----------------
        if isinstance(node, ClassDef):
            lines = [f"{self.indent()}class {node.name}:"]
            self.current_py_line += 1 # Account for class def line
            self.indent_level += 1

            # 1. Identify Constructor (Method name == Class name)
            ctor = None
            for m in node.methods:
                if m.name == node.name:
                    ctor = m
                    break

            # 2. Build Python __init__
            lines.append(f"{self.indent()}def __init__(self, *args):")
            self.current_py_line += 1
            self.indent_level += 1
            
            lines.append(f"{self.indent()}nargin = len(args)")
            self.current_py_line += 1

            # Initialize Properties
            if node.properties:
                for p in node.properties:
                    lines.append(f"{self.indent()}self.{p} = None")
                    self.current_py_line += 1

            # Transpile Constructor Body
            if ctor:
                # Unpack args manually
                for i, arg in enumerate(ctor.args):
                    lines.append(f"{self.indent()}{arg} = args[{i}] if nargin > {i} else None")
                    self.current_py_line += 1

                if ctor.outputs:
                    obj_var = ctor.outputs[0]
                    lines.append(f"{self.indent()}{obj_var} = self")
                    self.current_py_line += 1
                
                for stmt in ctor.body:
                    self._append_stmt(lines, stmt)
            else:
                lines.append(f"{self.indent()}pass")
                self.current_py_line += 1

            self.indent_level -= 1 # Exit __init__

            # 3. Transpile Other Methods
            for m in node.methods:
                if m == ctor: continue

                lines.append(f"\n{self.indent()}def {m.name}(self, *args):")
                self.current_py_line += 2 # Newline + def line
                self.indent_level += 1

                # Calculate nargin (includes implicit self)
                lines.append(f"{self.indent()}nargin = 1 + len(args)")
                self.current_py_line += 1

                if m.args:
                    obj_var = m.args[0]
                    lines.append(f"{self.indent()}{obj_var} = self")
                    self.current_py_line += 1
                    
                    # Unpack remaining args (skip self at index 0)
                    for i, arg in enumerate(m.args[1:]):
                        if arg == "varargin":
                             lines.append(f"{self.indent()}varargin = cell(list(args[{i}:]))")
                             self.current_py_line += 1
                             break
                        lines.append(f"{self.indent()}{arg} = args[{i}] if len(args) > {i} else None")
                        self.current_py_line += 1

                for stmt in m.body:
                    self._append_stmt(lines, stmt)

                if m.outputs:
                    ret = ", ".join(m.outputs)
                    lines.append(f"{self.indent()}return {ret}")
                    self.current_py_line += 1

                self.indent_level -= 1

            self.indent_level -= 1 # Exit class
            return "\n".join(lines)

        # ---------------- FunctionDef ----------------
        if isinstance(node, FunctionDef):
            header = f"def {node.name}(*args):"
            self.indent_level += 1
            body_lines = []
            
            # 1. Calculate nargin
            body_lines.append(self.indent() + "nargin = len(args)")

            # 2. Unpack arguments manually
            for i, arg_name in enumerate(node.args):
                if arg_name == "varargin":
                    # varargin captures remaining args into a cell array
                    body_lines.append(self.indent() + f"varargin = cell(list(args[{i}:]))")
                    break
                else:
                    # Support optional args by checking nargin
                    body_lines.append(self.indent() + f"{arg_name} = args[{i}] if nargin > {i} else None")

            # 3. Generate Body
            for stmt in node.body:
                self._append_stmt(body_lines, stmt)
            
            # GENERATE RETURN INSIDE FUNCTION SCOPE
            if node.outputs:
                ret = ", ".join(node.outputs)
                body_lines.append(self.indent() + f"return {ret}")

            self.indent_level -= 1 # Exit function

            return header + "\n" + "\n".join(body_lines)

        # ---------------- MultiAssign ----------------
        if isinstance(node, MultiAssign):
            lhs = ", ".join(node.targets)
            rhs = self.generate(node.value)
            return f"{self.indent()}{lhs} = {rhs}"

        # ---------------- Assign ----------------
        if isinstance(node, Assign):
            # 1. Generate RHS
            rhs = self.generate(node.value)
            
            # 2. Check for Indexed Assignment: A(1) = val
            if isinstance(node.target, Call): 
                 func_node = node.target.func
                 
                 # Extract name directly if it's a Variable to avoid auto-call syntax (e.g. 'clc()')
                 if isinstance(func_node, Variable):
                     func_str = func_node.name
                 else:
                     func_str = self.generate(func_node)
                     
                 args = ", ".join(self.generate(a) for a in node.target.args)
                 
                 # Use raw value for set_val
                 val_raw = self.generate(node.value) 
                 
                 assign_stmt = f"{func_str}.set_val({val_raw}, {args})"

                 # Handle Implicit Initialization: A(4) = 3
                 # If 'A' is a simple variable, we must ensure it exists.
                 if isinstance(func_node, Variable):
                     indent = self.indent()
                     sub = indent + "    "
                     return (
                         f"{indent}try:\n"
                         f"{sub}{func_str}\n"
                         f"{indent}except NameError:\n"
                         f"{sub}{func_str} = mat([])\n"
                         f"{indent}{assign_stmt}"
                     )
                 
                 return f"{self.indent()}{assign_stmt}"

            # 3. Normal Assignment
            target_str = ""
            if isinstance(node.target, Member):
                target_str = f"{self.generate(node.target.target)}.{node.target.field}"
            else:
                target_str = self.generate(node.target) if not isinstance(node.target, str) else node.target

            # 4. Copy-on-Write (Lazy Copy) Logic
            # Replaced eager .copy() with shared view using new MatlabArray constructor
            if isinstance(node.value, (Variable, Member)):
                 rhs = f"MatlabArray({rhs}, copy=False)"
            
            return f"{self.indent()}{target_str} = {rhs}"

        # ---------------- Return ----------------
        if isinstance(node, Return):
            if node.value is None:
                return self.indent() + "return"
            return self.indent() + f"return {self.generate(node.value)}"

        # ---------------- Binary Operators ----------------
        if isinstance(node, BinOp):
            l = self.generate(node.left)
            r = self.generate(node.right)
            
            if node.op == '&&': return f"({l} and {r})"
            if node.op == '||': return f"({l} or {r})"
            if node.op == '~=': return f"({l} != {r})"
            
            if node.op == '.*': return f"({l}).emul({r})"
            if node.op == './': return f"({l}).ediv({r})"
            if node.op == '.^': return f"({l}).epow({r})"
            if node.op == '^':  return f"({l} ** {r})"
            if node.op == '\\': return f"({l}.mldivide({r}))"
            
            return f"({l} {node.op} {r})"

        # ---------------- Unary Operators ----------------
        if isinstance(node, UnaryOp):
            val = self.generate(node.operand)
            if node.op == '~': return f"(~{val})"
            return f"({node.op}{val})"

        # ---------------- IfBlock ----------------
        if isinstance(node, IfBlock):
            lines = []
            for i, (cond, body) in enumerate(node.conditions):
                tag = "if" if i == 0 else "elif"
                lines.append(f"{self.indent()}{tag} {self.generate(cond)}:")
                self.indent_level += 1
                if body:
                    for stmt in body:
                        self._append_stmt(lines, stmt)
                else:
                    lines.append(self.indent() + "pass")
                self.indent_level -= 1

            if node.else_body is not None:
                lines.append(f"{self.indent()}else:")
                self.indent_level += 1
                for stmt in node.else_body:
                    self._append_stmt(lines, stmt)
                self.indent_level -= 1

            return "\n".join(lines)

        # ---------------- TryBlock ----------------
        if isinstance(node, TryBlock):
            lines = [f"{self.indent()}try:"]
            self.indent_level += 1
            if node.try_body:
                for stmt in node.try_body:
                    self._append_stmt(lines, stmt)
            else:
                lines.append(self.indent() + "pass")
            self.indent_level -= 1
            
            # [FIX] Safe fallback to internal variable `_catch_err` instead of overwriting workspace `ans`
            var = node.catch_var if node.catch_var else "_catch_err" 
            lines.append(f"{self.indent()}except Exception as {var}:")
            
            self.indent_level += 1
            if node.catch_body:
                for stmt in node.catch_body:
                    self._append_stmt(lines, stmt)
            else:
                lines.append(self.indent() + "pass")
            self.indent_level -= 1
            
            return "\n".join(lines)

        # ---------------- SwitchBlock ----------------
        if isinstance(node, SwitchBlock):
            # [FIX] Generate a unique identifier to prevent variable collision with nested switch statements
            switch_var = f"_switch_val_{id(node)}" 
            lines = [f"{self.indent()}{switch_var} = {self.generate(node.expression)}"]
            
            for i, (case_expr, body) in enumerate(node.cases):
                tag = "if" if i == 0 else "elif"
                
                if isinstance(case_expr, CellArray):
                    vals = []
                    for row in case_expr.rows:
                        for item in row:
                            vals.append(self.generate(item))
                    val_str = f"({', '.join(vals)})"
                    cond = f"{switch_var} in {val_str}"
                else:
                    val_str = self.generate(case_expr)
                    cond = f"{switch_var} == {val_str}"
                
                lines.append(f"{self.indent()}{tag} {cond}:")
                
                self.indent_level += 1
                if body:
                    for stmt in body:
                        self._append_stmt(lines, stmt)
                else:
                    lines.append(self.indent() + "pass")
                self.indent_level -= 1
                
            if node.otherwise_body:
                lines.append(f"{self.indent()}else:")
                self.indent_level += 1
                for stmt in node.otherwise_body:
                    self._append_stmt(lines, stmt)
                self.indent_level -= 1
                
            return "\n".join(lines)

        # ---------------- ForLoop ----------------
        if isinstance(node, ForLoop):
            header = f"{self.indent()}for {node.var} in {self.generate(node.iterable)}:"
            self.indent_level += 1
            body = []
            for stmt in node.body:
                self._append_stmt(body, stmt)
            self.indent_level -= 1
            return header + "\n" + "\n".join(body)

        # ---------------- WhileLoop ----------------
        if isinstance(node, WhileLoop):
            header = f"{self.indent()}while {self.generate(node.condition)}:"
            self.indent_level += 1
            body = []
            for stmt in node.body:
                self._append_stmt(body, stmt)
            self.indent_level -= 1
            return header + "\n" + "\n".join(body)

        # ---------------- Break / Continue ----------------
        if isinstance(node, Break): return self.indent() + "break"
        if isinstance(node, Continue): return self.indent() + "continue"

        # ---------------- Globals ----------------
        if isinstance(node, GlobalDecl):
            return f"{self.indent()}global {', '.join(node.names)}"

        # ---------------- Command ----------------
        if isinstance(node, Command):
            args = ", ".join(repr(a) for a in node.args)
            return f"{self.indent()}{node.name}({args})"

        # ---------------- Range ----------------
        if isinstance(node, Range):
            s = self.generate(node.start)
            e = self.generate(node.end)
            st = self.generate(node.step) if node.step else "1"
            return f"arange({s}, {e}, {st})"

        # ---------------- Call ----------------
        if isinstance(node, Call):
            if isinstance(node.func, str):
                func_str = node.func
            elif isinstance(node.func, Variable):
                func_str = node.func.name
            else:
                func_str = self.generate(node.func)
            
            args = ", ".join(self.generate(a) for a in node.args)
            return f"{func_str}({args})"

        # ---------------- Member ----------------
        if isinstance(node, Member):
            target = self.generate(node.target)
            return f"{target}.{node.field}"

        # ---------------- Index (Universal Call Fix) ----------------
        if isinstance(node, Index):
            # OLD: Generated python slices A[1:10] which caused ambiguity (A(1) vs sin(1))
            # NEW: Generate standard call syntax A(1:10).
            # The runtime MatlabArray.__call__ logic will distinguish index vs function call.
            target = self.generate(node.target)
            
            args = []
            for a in node.args:
                args.append(self.generate(a))
            
            arg_str = ", ".join(args)
            return f"{target}({arg_str})"

        # ---------------- Anonymous Function ----------------
        if isinstance(node, AnonymousFunc):
            args = ", ".join(node.args)
            body = self.generate(node.body)
            return f"(lambda {args}: {body})"

        # ---------------- Matrix / Cell ----------------
        if isinstance(node, Matrix):
            rows = ", ".join([f"[{', '.join(self.generate(x) for x in r)}]" for r in node.rows])
            return f"mat([{rows}])"

        if isinstance(node, CellArray):
            rows = ", ".join([f"[{', '.join(self.generate(x) for x in r)}]" for r in node.rows])
            return f"cell([{rows}])"

        # ---------------- Terminals ----------------
        if isinstance(node, Number): return node.value
        
        if isinstance(node, String):
            if node.value == ':':
                return "colon"
            return repr(node.value)
            
        if isinstance(node, Variable): 
            if node.name in AUTO_CALL_COMMANDS:
                return f"{node.name}()"
            return node.name

        return ""


def transpile(code: str):
    """
    Returns: (python_code, line_map)
    """
    if not code.strip():
        return "", {}
    try:
        tokens = Tokenizer(code).tokenize()
        tree = Parser(tokens).parse()
        
        compiler = ASTCompiler()
        
        # Manually drive the top-level generation to capture lines
        if isinstance(tree, Program):
            lines = []
            for stmt in tree.stmts:
                compiler._append_stmt(lines, stmt)
            py_code = "\n".join(lines)
        else:
            py_code = compiler.generate(tree)
            
        return py_code, compiler.line_map
        
    except Exception as e:
        return f"raise SyntaxError({repr(str(e))})", {}