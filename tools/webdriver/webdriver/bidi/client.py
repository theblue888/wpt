import asyncio
import functools
import json

from urllib.parse import urljoin, urlparse
from collections import defaultdict

import websockets


class BidiException(Exception):
    def __init__(self, err, msg, stack=None):
        self.err = err
        self.msg = msg
        self.stack = stack


class BidiSession:
    def __init__(self, websocket_url, capabilities, session_id=None, loop=None):
        self.transport = None
        self.websocket_url = websocket_url
        self.capabilities = capabilities
        self.session_id = session_id

        self.command_id = 0
        self.pending_commands = {}
        self.event_listeners = defaultdict(list)

        # Modules
        self.session = Session(self)

        if loop is None:
            loop = asyncio.get_running_loop()
        self.loop = loop

    @staticmethod
    def set_capability(caps):
        if caps:
            caps.setdefault("alwaysMatch", {}).update({"webSocketUrl": True})
        else:
            caps = {"alwaysMatch": {"webSocketUrl": True}}

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.end()

    async def start(self):
        """Start a new WebDriver Bidirectional session
        with websocket connected.
        """
        if urlparse(self.websocket_url).path == "/":
            if self.session_id is None:
                self.websocket_url = urljoin(self.websocket_url, "session")
            else:
                self.websocket_url = urljoin(self.websocket_url, "session/%s" % self.session_id)
        self.transport = Transport(self.websocket_url, self.on_message, loop=self.loop)

        if self.session_id is None:
            await self.session.new(self.capabilities)

        await self.transport.start()

    async def send_command(self, method, params):
        # this isn't threadsafe
        self.command_id += 1
        command_id = self.command_id

        body = {
            "id": command_id,
            "method": method,
            "params": params
        }
        self.pending_commands[command_id] = self.loop.create_future()
        await self.transport.send(body)

        return self.pending_commands[command_id]

    async def on_message(self, data):
        if "id" in data:
            # This is a command response or error
            future = self.pending_commands.get(data["id"])
            if future is None:
                raise ValueError("No pending command with id %s" % data["id"])
            if "result" in data:
                future.set_result(data["result"])
            elif "error" in data and "message" in data:
                future.set_exception(BidiException(data["error"],
                                                   data["message"],
                                                   data.get("stacktrace")))
            else:
                raise ValueError("Unexpected message: %r" % data)
        elif "method" in data and "params" in data:
            # This is an event
            method = data["method"]
            listeners = self.event_listeners.get(method)
            if not listeners:
                listeners = self.event_listeners[None]
            for listener in listeners:
                await listener(data["params"])
        else:
            raise ValueError("Unexpected message: %r" % data)

    async def end(self):
        """Close websocket connection first before closing session.
        """
        await self.transport.end()

    def add_event_listener(self, name, fn):
        self.event_listeners[name].append(fn)


class Transport:
    def __init__(self, url, msg_handler, loop=None):
        self.url = url
        self.connection = None
        self.msg_handler = msg_handler
        self.send_buf = []

        if loop is None:
            loop = asyncio.get_running_loop()
        self.loop = loop

        self.read_message_task = None

    async def start(self):
        self.connection = await websockets.client.connect(self.url)
        self.read_message_task = self.loop.create_task(self.read_messages())

        for msg in self.send_buf:
            await self._send(msg)

    async def send(self, data):
        if self.connection:
            await self._send(data)
        else:
            self.send_buf.append(data)

    async def _send(self, data):
        msg = json.dumps(data)
        print(msg)
        await self.connection.send(msg)

    async def handle(self, msg):
        data = json.loads(msg)
        await self.msg_handler(data)

    async def end(self):
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def read_messages(self):
        async for msg in self.connection:
            print(msg)
            await self.handle(msg)


class command:
    """Decorator for implementing bidi commands

    Implementing a command involves specifying an async function that
    builds the parameters to the command. The decorator arranges those
    parameters to be turned into a send_command call, using the class
    and method names to determine the method in the call.

    Commands decorated in this way don't return a future, but await
    the actual response. In some cases it can be useful to
    post-process this response before returning it to the client. This
    can be done by specifying a second decorated method like
    @command_name.result. That method will then be called once the
    result of the original command is known, and the return value of
    the method used as the response of the command.

    So for an example, if we had a command test.testMethod, which
    returned a result which we want to convert to a TestResult type,
    the implementation might look like:

    class Test(BidiModule):
        @command
        def test_method(self, test_data=None):
            return {"testData": test_data}

       @test_method.result
       def _test_method(self, result):
           return TestData(**result)
    """

    def __init__(self, fn):
        self.params_fn = fn
        self.result_fn = None

    def result(self, fn):
        self.result_fn = fn

    def __set_name__(self, owner, name):
        params_fn = self.params_fn
        result_fn = self.result_fn

        @functools.wraps(params_fn)
        async def inner(self, **kwargs):
            params = params_fn(self, **kwargs)
            mod_name = owner.__name__.lower()
            if hasattr(owner, "prefix"):
                mod_name = "%s:%s" % (owner.prefix, mod_name)
            cmd_name = "%s.%s" % (mod_name,
                                  to_camelcase(name))
            future = await self.session.send_command(cmd_name, params)
            result = await future
            if result_fn is not None:
                result = result_fn(self, result)
            return result

        setattr(owner, name, inner)


def to_camelcase(name):
    parts = name.split("_")
    parts[0] = parts[0].lower()
    for i in range(1, len(parts)):
        parts[i] = parts[i].title()
    return "".join(parts)


class BidiModule:
    def __init__(self, session):
        self.session = session


class Session(BidiModule):
    @command
    def new(self, capabilities):
        return {"capabilities": capabilities}

    @new.result
    def _new(self, result):
        return result["capabilities"]

    @command
    def subscribe(self, events=None, contexts=None):
        params = {"events": events if events is not None else []}
        if contexts is not None:
            params["contexts"] = None
        return params

    @command
    def unsubscribe(self, events=None, contexts=None):
        params = {"events": events if events is not None else []}
        if contexts is not None:
            params["contexts"] = None
        return params


class Test(BidiModule):
    """Very temporary module that does nothing, except demonstrate a vendor prefix and
    provide a way to work with Gecko's current skeleton implementation."""

    prefix = "moz"

    @command
    def test_method(self, **kwargs):
        return kwargs
