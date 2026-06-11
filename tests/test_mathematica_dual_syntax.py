from ides.mathematica.kernel.dual_syntax import normalize_dual_syntax
from ides.mathematica.kernel.engine import MathematicaBackend
from shared.config import AppConfig


def _with_language(lang, fn):
    previous = AppConfig.get_language()
    AppConfig.set_language(lang)
    try:
        return fn()
    finally:
        AppConfig.set_language(previous)


def test_normalize_dual_syntax_supports_lowercase_wolfram_commands():
    assert normalize_dual_syntax("plot[Sin[x], {x, -1, 1}]") == "Plot[Sin[x], {x, -1, 1}]"
    assert normalize_dual_syntax("simplify[x^2 + 2 x + 1]") == "Simplify[x^2 + 2 x + 1]"


def test_normalize_dual_syntax_supports_assamese_command_heads():
    assert normalize_dual_syntax("\u0986\u0981\u0995\u09be[Sin[x], {x, -1, 1}]") == "Plot[Sin[x], {x, -1, 1}]"
    assert normalize_dual_syntax("\u09b8\u09ae\u09be\u0995\u09b2\u09a8[x^2, x]") == "Integrate[x^2, x]"
    assert normalize_dual_syntax("\u09b8\u09c0\u09ae\u09be[Sin[x]/x, x -> 0]") == "Limit[Sin[x]/x, x -> 0]"


def test_mathematica_backend_dual_syntax_assignment_and_eval():
    def run():
        backend = MathematicaBackend()
        assign_html = backend.execute("a = 5")
        result_html = backend.execute("\u09b8\u09ae\u09be\u09a7\u09be\u09a8[a + x == 9, x]")

        assert "a =" in assign_html
        assert "x" in result_html
        assert "4" in result_html

    _with_language("en", run)


def test_mathematica_backend_steps_supports_algebra_commands():
    def run():
        backend = MathematicaBackend()
        result_html = backend.execute("Steps[Simplify[(x^2 - 1)/(x - 1)]]")

        assert "Steps" in result_html
        assert "x + 1" in result_html

    _with_language("en", run)


def test_mathematica_backend_nsteps_supports_quadratic_equations():
    def run():
        backend = MathematicaBackend()
        result_html = backend.execute("NSteps[x^2 - 5 x + 6 == 0]")

        assert "Quadratic Equation Solution" in result_html
        assert "2" in result_html
        assert "3" in result_html

    _with_language("en", run)


def test_mathematica_backend_steps_supports_solver_command():
    def run():
        backend = MathematicaBackend()
        result_html = backend.execute("Steps[Solve[x^3 - 6 x^2 + 11 x - 6 == 0, x]]")

        assert "Polynomial Equation Solution" in result_html
        assert "1" in result_html
        assert "2" in result_html
        assert "3" in result_html

    _with_language("en", run)


def test_mathematica_backend_steps_localize_to_assamese():
    def run():
        backend = MathematicaBackend()
        result_html = backend.execute("Steps[Solve[x^2 - 5 x + 6 == 0, x]]")

        assert "দ্বিঘাত সমীকৰণৰ সমাধান" in result_html
        assert "ফলাফল" in result_html

    _with_language("as", run)
