import pytest

from templar.core.Reactive import State
from templar.core.Javascript import Javascript
from templar.core.elements.Div import Div
from templar.core.elements.Element import Element
from templar.RequestHandler import RequestHandler
from templar.Context import TemplarContext


def test_reactive_state_json_cannot_close_its_script_tag():
    rendered = State("profile", bio="</script><script>alert(1)</script>&\u2028\u2029").render().render()

    assert "</script><script>alert(1)</script>" not in rendered
    assert "\\u003C/script\\u003E\\u003Cscript\\u003Ealert(1)\\u003C/script\\u003E\\u0026\\u2028\\u2029" in rendered


def test_reactive_state_requires_a_safe_javascript_identifier():
    with pytest.raises(ValueError, match="JavaScript identifiers"):
        State("profile; alert(1)")


def test_reactive_html_binding_requires_an_explicit_unsafe_opt_in():
    safe_output = State("profile", bio="<img onerror=alert(1)>").bind_text("bio", "#bio").render().render()
    unsafe_output = State("profile", bio="<strong>trusted</strong>").bind_html_unsafe("bio", "#bio").render().render()

    assert '"type": "html_unsafe"' not in safe_output
    assert 'binding.type === "html_unsafe"' in unsafe_output
    assert not hasattr(State("profile"), "bind_html")


def test_reactive_attributes_reject_browser_execution_sinks_by_default():
    state = State("profile", label="safe")
    assert state.bind_attr("label", "#field", "title") is state

    with pytest.raises(ValueError, match="bind_attr_unsafe"):
        state.bind_attr("label", "#field", "onclick")

    assert state.bind_attr_unsafe("label", "#field", "onclick") is state


def test_javascript_helpers_cannot_close_their_inline_script_tag():
    rendered = Javascript().css("#profile", color="</script><script>alert(1)</script>").render()

    assert "</script><script>alert(1)</script>" not in rendered
    assert "\\x3C/script\\x3E" in rendered


def test_elements_reject_unsafe_or_malformed_attribute_names():
    with pytest.raises(ValueError, match="Unsafe HTML attribute"):
        Div(**{"onmouseover": "alert(1)"}).render()

    with pytest.raises(ValueError, match="Invalid HTML attribute"):
        Div(**{'x" onmouseover="alert(1)': "value"}).render()


def test_elements_reject_untrusted_tag_names():
    with pytest.raises(ValueError, match="Invalid HTML tag name"):
        Element("img src=x onerror=alert(1)")


def test_response_header_helpers_reject_response_splitting_characters():
    context = TemplarContext(None, None, "GET", "/", {}, {}, {})

    with pytest.raises(ValueError, match="response header"):
        context.set_header("X-Redirect", "ok\r\nSet-Cookie: injected=true")

    with pytest.raises(ValueError, match="response header"):
        context.set_header("X Bad", "value")


def test_elements_reject_executable_url_schemes_but_allow_safe_urls():
    assert 'href="https://example.test/path"' in Div(**{"href": "https://example.test/path"}).render()
    assert 'href="/account"' in Div(**{"href": "/account"}).render()

    with pytest.raises(ValueError, match="Unsafe URL scheme"):
        Div(**{"href": "java\nscript:alert(1)"}).render()

    with pytest.raises(ValueError, match="Unsafe URL scheme"):
        Div(**{"src": "data:text/html,<script>alert(1)</script>"}).render()

    with pytest.raises(ValueError, match="Unsafe URL scheme"):
        Div(**{"srcset": "https://example.test/one.png 1x, javascript:alert(1) 2x"}).render()


def test_http_access_logs_redact_query_strings_before_console_rendering():
    handler = object.__new__(RequestHandler)
    handler.path = "/reset?token=private-value"
    handler.address_string = lambda: "127.0.0.1"

    handler.log_message('"%s" %s %s', "GET /reset?token=private-value HTTP/1.1", "200", "-")

    assert handler._log_buffer == ['[HTTP] 127.0.0.1 - "GET /reset HTTP/1.1" 200 -']
