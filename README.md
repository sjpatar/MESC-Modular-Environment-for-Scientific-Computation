# MESC: Modular Environment for Scientific Computation

![Status](https://img.shields.io/badge/Status-Active_Development-success.svg) ![Python](https://img.shields.io/badge/Python-3.11+-blue.svg) ![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg) ![License](https://img.shields.io/badge/License-MIT-blue.svg)

**MESC** (Modular Environment for Scientific Computation) is an advanced, offline-first desktop application designed to unify powerful STEM workflows into a single, cohesive workspace. Built with Python and Qt, it serves as a bridge between high-level mathematics, physics simulations, and accessible native-language interfaces.

Think of it as an **Operating System for Science**—a lightweight, extensible shell that runs specialized IDEs and tools without the heavy overhead of monolithic software.

---

## 📖 Why I Created This App

As a Computer Science student, I noticed that scientific computing environments are heavily fragmented and almost exclusively English-centric. Students, researchers, and engineers often have to juggle multiple heavy applications for symbolic math, numerical arrays, and geometric visualization. Furthermore, these tools either require constant internet connections, expensive licenses, or lack support for regional languages, creating a barrier to entry.

My goal with MESC was to build an **organization-level, production-ready environment** that solves these problems from the ground up:
1. **Unification:** Merging the capabilities of tools like MATLAB, Mathematica, and Geogebra into a single, tabbed shell.
2. **True Offline Capability:** Engineering the application to run complex LaTeX rendering and interactive 3D plots without a single external network request or CDN dependency.
3. **Native Accessibility:** Implementing a deep localization engine that allows users to write advanced mathematical syntax natively in Assamese, complete with phonetic translation, while seamlessly preserving standard English algebraic variables for universal compatibility.

---

## 🏗️ System Architecture (How It Was Built)

MESC is built on a strict **Clean Architecture** paradigm, ensuring that core computation logic is entirely decoupled from the UI. 

### 1. The Platform Shell (`app_platform`)
* **Frameless PySide6 Windowing:** A modern, custom-drawn window shell featuring a professional breadcrumb navigation system (similar to VS Code) that allows users to instantly switch between active tools (e.g., swapping from *Mathex* to *Mathematica*).
* **Shared Core (`shared`):** A centralized repository of math engines and plotting libraries. It features unified access to SymPy/NumPy and a high-performance Matplotlib wrapper that handles figure docking for any connected tool.

### 2. The WebEngine Bridge & Storage Architecture
To achieve beautiful, notebook-style interfaces with rich mathematical rendering, the app injects a Chromium backend (`QWebEngineView`). 
* **The "Pull" Serialization Engine:** To bypass standard browser memory limits (the 32KB `console.log` limit) when saving massive notebooks, MESC uses a custom asynchronous "Pull" architecture. Python actively hooks into the DOM to extract complete session states and embedded SVG dictionaries, allowing users to save and load 100+ MB notebooks flawlessly.

### 3. Native Language & Dual-Syntax Interceptor
* **The Hybrid Pipeline:** Users can mix native Assamese keywords with universally standard mathematics. A custom regex interceptor safely captures and translates Assamese command heads (e.g., `সমাধান[]`, `লেখচিত্ৰ3D[]`) and native numerals (`০-৯`) into English for the SymPy kernel, while deliberately bypassing variables like `x`, `y`, or `Pi` to prevent breaking standard algebra.

---

## 🛠️ The IDE Plugins (`ides`)

The platform currently hosts three powerful modules:

### 🧮 1. Mathematica (Wolfram-Style Environment)
A symbolic-first environment designed for high-level algebraic manipulation and notebook-driven workflows.
* **Strict Terminal Paradigm:** Cells lock immutably upon execution to create a reliable mathematical audit trail (with double-click overrides for necessary edits).
* **True Offline MathJax:** Uses a strictly local SVG-caching configuration for MathJax. It renders beautiful LaTeX equations instantly without external CDNs, assistive workers, or web-font requests.
* **Interactive Plotting:** Integrates Matplotlib for 2D graphs and bundles Plotly directly into the HTML payload for zero-latency, offline 3D interactive plotting.
* **Variable Inspector & Simple Mode:** Features a real-time memory tracker and a toggleable "Simple Mode" for intuitive equation solving without strict syntactical rules.

### 🖥️ 2. Mathex (MATLAB® Compatible Workspace)
A transcript-based IDE that runs `.m` files, designed to replace legacy environments for engineers.
* **Custom AST Transpiler (`ides.mathex.language`):** A ground-up lexical analyzer and Recursive Descent Parser that translates MATLAB syntax into optimized Python bytecode on the fly (converting 1-based indexing to 0-based, injecting Copy-on-Write memory behavior, etc.).
* **Workspace Inspector:** An interactive data viewer featuring live 2D "Slice Views" (e.g., `[:,:,0]`) for massive 3D/4D arrays to prevent UI freezing.
* **Research Toolboxes:** Includes custom implementations for Partial Differential Equations (`pdepe`), Control Systems (`tf`, `bode`), and Optimization (`fmincon` via Scipy SLSQP).

### 📐 3. Geogebra Integration
A seamless, offline-capable module that brings advanced geometric constructions and interactive algebraic graphing directly into the MESC workspace.

---

## 💻 Tech Stack

MESC is built with high-performance Python and Web technologies:

| Component | Technology | Role |
| :--- | :--- | :--- |
| **GUI Framework** | **PySide6 (Qt)** | Native OS integration, dark mode, and frameless windowing. |
| **Browser Engine** | **Chromium (QWebEngine)** | Powers the rich text, JavaScript, and LaTeX rendering. |
| **Runtime** | **Python 3.11+** | Selected for speed and advanced type hinting. |
| **Math Engine** | **NumPy & SciPy** | Powers the linear algebra, signal processing, and ODE/PDE solvers. |
| **Symbolic Core** | **SymPy** | The backbone of the Mathematica tool and Symbolic logic. |
| **Rendering** | **Matplotlib & Plotly** | The engines behind the shared 2D/3D plotting system. |
| **Frontend** | **HTML5 / JS / MathJax** | Notebook interfaces, DOM manipulation, and offline SVG math rendering. |

## 📦 Installation & Setup

### Prerequisites
* Python 3.10 or higher.

### Steps

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/Prime01-oss/MESC.git](https://github.com/Prime01-oss/MESC.git)
    cd MESC
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Platform**
    ```bash
    python main.py
    ```

*Note: If you encounter import errors regarding `platform`, ensure you have run the `fix_imports.py` script included in the root directory to finalize the directory restructuring.*

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and create a pull request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## Author Details
**Samarjit Patar** 📧 patarsamar123abc@gmail.com