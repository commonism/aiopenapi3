import asyncio
import copy
import datetime
import decimal
import time

import aiopenapi3

from flask import Flask, render_template_string, redirect, url_for, Blueprint, abort
from flask_bootstrap import Bootstrap4 as Bootstrap
from flask_wtf import FlaskForm, CSRFProtect
from wtforms.fields import (
    BooleanField,
    DateField,
    DateTimeField,
    DateTimeLocalField,
    DecimalField,
    DecimalRangeField,
    EmailField,
    FileField,
    MultipleFileField,
    FloatField,
    IntegerField,
    IntegerRangeField,
    RadioField,
    SelectField,
    SearchField,
    SelectMultipleField,
    SubmitField,
    StringField,
    TelField,
    TimeField,
    URLField,
    HiddenField,
    PasswordField,
    TextAreaField,
)

from wtforms.validators import DataRequired, NumberRange
from flask import request, Response

from asgiref.wsgi import WsgiToAsgi

import pytest
import pytest_asyncio

import uvloop
from hypercorn.asyncio import serve
from hypercorn.config import Config

# csrf.exempt(serve_test)

bp = Blueprint("slash", __name__)


class DateTimeForm(FlaskForm):
    class Meta:
        csrf = False

    time = TimeField(format="%H:%M:%S.%f", validators=[DataRequired()])
    date = DateField(validators=[DataRequired()])
    datetime = DateTimeField(format="%Y-%m-%d %H:%M:%S.%f%z", validators=[DataRequired()])
    datetimelocal = DateTimeLocalField(format="%Y-%m-%d %H:%M:%S.%f", validators=[DataRequired()])


class NumbersForm(FlaskForm):
    class Meta:
        csrf = False

    boolean = BooleanField(validators=[DataRequired()])
    decimal = DecimalField(validators=[DataRequired()])
    decimalrange = DecimalRangeField(validators=[NumberRange(min=0, max=10), DataRequired()])
    float = FloatField(validators=[DataRequired()])
    integer = IntegerField(validators=[DataRequired()])
    integerrange = IntegerRangeField(validators=[NumberRange(min=0, max=10), DataRequired()])


class FileForm(FlaskForm):
    class Meta:
        csrf = False

    file = FileField(validators=[DataRequired()])
    files = MultipleFileField(validators=[DataRequired()])
    xml = FileField(validators=[DataRequired()])


class SelectForm(FlaskForm):
    CHOICES = [("cpp", "C++"), ("py", "Python"), ("txt", "Plain Text"), ("rb", "Ruby"), ("c", "C")]

    class Meta:
        csrf = False

    radio = RadioField(choices=CHOICES, validators=[DataRequired()])
    select = SelectField(choices=CHOICES, validators=[DataRequired()])
    selectmultiple = SelectMultipleField(choices=CHOICES, validators=[DataRequired()])


class StringForm(FlaskForm):
    class Meta:
        csrf = False

    string = StringField(validators=[DataRequired()])
    tel = TelField(validators=[DataRequired()])
    url = URLField(validators=[DataRequired()])
    hidden = HiddenField(validators=[DataRequired()])
    password = PasswordField(validators=[DataRequired()])
    textareafield = TextAreaField(validators=[DataRequired()])
    email = EmailField(validators=[DataRequired()])


class ControlForm(FlaskForm):
    class Meta:
        csrf = False

    search = SearchField(validators=[DataRequired()])
    submit = SubmitField(validators=[DataRequired()])


class HeaderForm(FlaskForm):
    class Meta:
        csrf = False

    header = StringField(validators=[DataRequired()])


class StarForm(FlaskForm):
    class Meta:
        csrf = False

    star = StringField(validators=[DataRequired()])


class MyTestsForm(FlaskForm):
    class Meta:
        csrf = False

    string = StringField("string", validators=[DataRequired()])
    number = IntegerField("number", validators=[DataRequired()])


TEMPLATE = """
{% extends 'bootstrap/base.html' %}
{% import "bootstrap/wtf.html" as wtf %}
{% block content %}
{{ wtf.quick_form(form, enctype='{enctype}') }}
{% endblock %}
"""


@bp.route("/string", methods=["GET", "POST"])
def serve_string():
    form = StringForm()
    return render(form)


@bp.route("/datetime", methods=["GET", "POST"])
def serve_datetime():
    form = DateTimeForm()
    return render(form)


@bp.route("/numbers", methods=["GET", "POST"])
def serve_numbers():
    form = NumbersForm()
    return render(form)


@bp.route("/file", methods=["GET", "POST"])
def serve_file():
    form = FileForm()
    return render(form)


@bp.route("/select", methods=["GET", "POST"])
def serve_select():
    form = SelectForm()
    return render(form)


@bp.route("/control", methods=["GET", "POST"])
def serve_control():
    form = ControlForm()
    return render(form)


@bp.route("/header", methods=["GET", "POST"])
def serve_header():
    form = HeaderForm()
    return render(form)


@bp.route("/star", methods=["GET", "POST"])
def serve_star():
    form = StarForm()
    return render(form)


@bp.route("/test", methods=["GET", "POST"])
def serve_test():
    form = MyTestsForm()
    return render(form)


def render(form: FlaskForm, enctype: str = "multipart/form-data"):
    if request.method == "POST":
        if form.validate_on_submit():
            return Response('"ok"', content_type="application/json")
        elif form.errors:
            abort(501, str(form.errors))
        else:
            abort(502)
    else:
        return render_template_string(TEMPLATE, enctype=enctype, form=form)


def create_app(args=None):
    app = Flask(__name__)

    # Flask-WTF requires an encryption key - the string can be anything
    app.config["SECRET_KEY"] = "4711"
    if args:
        app.config.update(args)

    app.register_blueprint(bp)

    # Flask-Bootstrap requires this line
    Bootstrap(app)
    return app


@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
        }
    )

    # other setup can go here
    yield app
    # clean up / reset resources here


@pytest.fixture()
def fclient(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


def test_config():
    assert not create_app().testing
    assert create_app({"TESTING": True}).testing


def test_hello(fclient):
    response = fclient.post("/test", data={"string": "a", "number": 1})
    assert response.data == b'"ok"'


@pytest.fixture(scope="session")
def config(unused_tcp_port_factory):
    c = Config()
    c.bind = [f"localhost:{unused_tcp_port_factory()}"]
    return c


@pytest_asyncio.fixture(scope="session")
async def server(event_loop, config, app):
    policy = asyncio.get_event_loop_policy()
    try:
        sd = asyncio.Event()
        asgi = WsgiToAsgi(app)
        task = event_loop.create_task(serve(asgi, config, shutdown_trigger=sd.wait))
        yield config
    finally:
        sd.set()
        del asgi
        await task
    asyncio.set_event_loop_policy(policy)


@pytest.fixture(scope="session", params=["application/x-www-form-urlencoded", "multipart/form-data"])
def form_type(request):
    return f"{request.param}"


@pytest_asyncio.fixture(scope="session")
async def client(server, form_type, with_paths_requestbody_formdata_wtforms):
    data = copy.deepcopy(with_paths_requestbody_formdata_wtforms)
    if form_type != "multipart/form-data":
        for op, v in data["paths"].items():
            v["post"]["requestBody"]["content"][form_type] = v["post"]["requestBody"]["content"]["multipart/form-data"]
            del v["post"]["requestBody"]["content"]["multipart/form-data"]

    data["servers"][0]["url"] = f"http://{server.bind[0]}"
    api = aiopenapi3.OpenAPI("/", data)
    return api


@pytest.mark.asyncio
async def _test_service(event_loop, server, client):
    while True:
        await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_Test(event_loop, server, client, form_type):
    cls = client._.test.operation.requestBody.content[form_type].schema_.get_type()
    data = cls(string="yes", number="5", file="test")

    r = await client._.test(data=data, parameters={"Accept": form_type})
    assert r == "ok"


@pytest.mark.asyncio
async def test_String(event_loop, server, client, form_type):
    cls = client._.string.operation.requestBody.content[form_type].schema_.get_type()
    data = cls(
        string="yes",
        tel="0494711",
        url="https://example.org",
        hidden="hidden",
        password="s3cr3t",
        textareafield="long text",
        email="noreply@example.org",
    )

    r = await client._.string(data=data)
    assert r == "ok"


@pytest.mark.asyncio
async def test_DateTime(event_loop, server, client, form_type):
    cls = client._.datetime.operation.requestBody.content[form_type].schema_.get_type()
    now = datetime.datetime.now()

    data = cls(
        time=now.time(), date=now.date(), datetime=datetime.datetime.now(tz=datetime.timezone.utc), datetimelocal=now
    )

    r = await client._.datetime(data=data)
    assert r == "ok"


@pytest.mark.asyncio
async def test_Numbers(event_loop, server, client, form_type):
    cls = client._.numbers.operation.requestBody.content[form_type].schema_.get_type()

    data = cls(
        boolean=True,
        decimal=decimal.Decimal(1 / 3),
        decimalrange=decimal.Decimal(2 / 3),
        float=float(1 / 3),
        integer=int(9),
        integerrange=int(9),
    )

    r = await client._.numbers(data=data)
    assert r == "ok"


@pytest.mark.asyncio
async def test_File(event_loop, server, client, form_type):
    cls = client._.file.operation.requestBody.content[form_type].schema_.get_type()

    data = cls(file=b"4711", files=[b"a", b"b"], xml=b"yes")

    r = await client._.file(data=data)
    assert r == "ok"


@pytest.mark.asyncio
async def test_Select(event_loop, server, client, form_type):
    cls = client._.select.operation.requestBody.content[form_type].schema_.get_type()

    data = cls(radio="py", select="rb", selectmultiple=["c", "cpp"])

    r = await client._.select(data=data)
    assert r == "ok"


@pytest.mark.asyncio
async def test_Control(event_loop, server, client, form_type):
    cls = client._.control.operation.requestBody.content[form_type].schema_.get_type()

    data = cls(submit="yes", search="no")

    r = await client._.control(data=data)
    assert r == "ok"


@pytest.mark.asyncio
async def test_Header(event_loop, server, client, form_type):
    if form_type != "multipart/form-data":
        pytest.skip()

    cls = client._.header.operation.requestBody.content[form_type].schema_.get_type()

    data = cls(
        header="head",
    )

    r = await client._.header(data=data, parameters={"X-HEADER": "header"})
    assert r == "ok"


@pytest.mark.asyncio
async def test_Graph(event_loop, server, client, form_type):
    if form_type != "multipart/form-data":
        pytest.skip()

    cls = client._.star.operation.requestBody.content[form_type].schema_.get_type()

    data = cls(star={"name": "Neptun", "position": "sky"})

    r = await client._.star(data=data)
    assert r == "ok"
