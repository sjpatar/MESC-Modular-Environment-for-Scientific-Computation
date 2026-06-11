class StepResult:
    """Carries rich HTML/LaTeX output for step-by-step solutions."""
    def __init__(self, html): 
        self.html = html
    
    def to_html(self): 
        return self.html

class SolutionResult:
    """Formats mathematical solutions (roots, sets) into Mathematica-style output."""
    def __init__(self, data): 
        self.data = data # List of dicts: [{x: 1}, {x: -1}]
        
    def __repr__(self):
        rules = []
        for d in self.data:
            rules.append("{" + ", ".join([f"{k} -> {v}" for k,v in d.items()]) + "}")
        return "{" + ", ".join(rules) + "}"

    def to_html(self):
        # Converts Python dicts to Mathematica rules: { x -> 1.5 }
        rules = []
        for d in self.data:
            inner = ", ".join([
                f"{k} &rarr; {float(v):.4f}" if hasattr(v, 'is_Float') and v.is_Float else f"{k} &rarr; {v}" 
                for k,v in d.items()
            ])
            rules.append(f"{{ {inner} }}")
        return str(rules).replace('[','{').replace(']','}').replace("'", "")