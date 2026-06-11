# Mathex/mathex/config/defaults.py
"""
Mathex global matplotlib defaults.
Max Potential: Research Standard Dark Theme
"""

from __future__ import annotations
import matplotlib
from cycler import cycler

def apply():
    """Apply Mathex 'Research Standard' Dark Theme."""
    try:
        rc = matplotlib.rcParams

        # ==========================================================
        # 1. LAYOUT & RESOLUTION
        # ==========================================================
        # Use 'constrained_layout' for professional spacing (prevents overlap)
        rc["figure.constrained_layout.use"] = True
        
        # High DPI for crisp rendering
        rc["figure.dpi"] = 100
        rc["savefig.dpi"] = 300
        rc["savefig.bbox"] = "tight"

        # ==========================================================
        # 2. TYPOGRAPHY
        # ==========================================================
        rc["font.family"] = "sans-serif"
        rc["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
        rc["font.size"] = 11
        rc["mathtext.fontset"] = "stixsans"  # Math matches text

        # ==========================================================
        # 3. COLORS (Neon/Pastel Hybrid for Dark Mode)
        # ==========================================================
        colors = [
            "#00E5FF",  # Cyan
            "#FF4081",  # Pink
            "#76FF03",  # Lime
            "#FFEA00",  # Yellow
            "#EA80FC",  # Violet
            "#FF9100",  # Orange
            "#FFFFFF"   # White
        ]
        rc["axes.prop_cycle"] = cycler(color=colors)

        # ==========================================================
        # 4. COMPONENT STYLING
        # ==========================================================
        bg_dark = "#1e1e1e"
        bg_lighter = "#252526"
        
        rc["figure.facecolor"] = bg_dark
        rc["axes.facecolor"] = bg_lighter
        rc["axes.edgecolor"] = "#666666"
        rc["axes.labelcolor"] = "#E0E0E0"
        rc["axes.titlecolor"] = "#FFFFFF"
        rc["text.color"] = "#E0E0E0"
        rc["xtick.color"] = "#CCCCCC"
        rc["ytick.color"] = "#CCCCCC"

        # ==========================================================
        # 5. DATA REPRESENTATION
        # ==========================================================
        rc["lines.linewidth"] = 2.0
        rc["lines.markersize"] = 7
        rc["axes.grid"] = True
        rc["grid.color"] = "#555555"
        rc["grid.linestyle"] = "-"
        rc["grid.linewidth"] = 0.6
        rc["grid.alpha"] = 0.4
        
        # Legend styling
        rc["legend.frameon"] = True
        rc["legend.framealpha"] = 0.9
        rc["legend.facecolor"] = "#2d2d2d"

    except Exception:
        pass