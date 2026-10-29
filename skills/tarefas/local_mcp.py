"""MCP stdio protocol 2025-06-18. One explicitly selected board, no filesystem tools.

https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle
"""
import sys
from local_store import LocalError, MAX_BODY, READS, WRITES, encode, parse_json

PROTOCOL = '2025-06-18'
PROPERTIES = {
    'op': {'type': 'string'},
    'collection': {'type': 'string', 'enum': ['tasks', 'dias', 'arquivo', 'recorrentes', 'config', 'indice']},
    'id': {'type': 'string'}, 'data': {'type': 'object'},
    'if_version': {'type': 'integer', 'minimum': 1},
    'mutation_id': {'type': 'string', 'description': 'Stable retry ID; repeat the exact request after an ambiguous response.'},
    'filters': {'type': 'array', 'description': 'Array of [field, operator, value] filters. Operators: ==, !=, in, array-contains, <, <=, >, >=.'},
    'limit': {'type': 'integer', 'minimum': 1, 'maximum': 1000}, 'cursor': {'type': 'string'},
    'operations': {'type': 'array', 'maxItems': 100, 'items': {'type': 'object'}},
}


def tool(name, operations, read):
    props = dict(PROPERTIES)
    props['op'] = {'type': 'string', 'enum': sorted(operations)}
    return {'name': name, 'description': ('Read' if read else 'Write') + ' documents in the configured local Cortex board. Existing writes require if_version; task index is maintained automatically. No board selection through tool arguments.',
            'inputSchema': {'type': 'object', 'properties': props, 'required': ['op'], 'additionalProperties': False},
            'annotations': {'readOnlyHint': read, 'destructiveHint': not read, 'idempotentHint': read, 'openWorldHint': False}}


def run(store, board, instream=None, outstream=None):
    source = instream or sys.stdin.buffer
    output = outstream or sys.stdout
    initialized = False
    ready = False
    tools = [tool('cortex_read', READS, True), tool('cortex_write', WRITES, False)]

    def send(message):
        output.write(encode(message) + '\n')
        output.flush()

    def error(ident, code, message):
        send({'jsonrpc': '2.0', 'id': ident, 'error': {'code': code, 'message': message}})

    while True:
        line = source.readline(MAX_BODY + 1)
        if not line:
            break
        if len(line) > MAX_BODY:
            # Discard the remainder without allocating an unbounded JSON string.
            while line and not line.endswith(b'\n'):
                line = source.readline(MAX_BODY + 1)
            error(None, -32700, 'Message exceeds size limit')
            continue
        try:
            msg = parse_json(line)
        except LocalError:
            error(None, -32700, 'Parse error')
            continue
        if not isinstance(msg, dict) or msg.get('jsonrpc') != '2.0' or not isinstance(msg.get('method'), str):
            error(None, -32600, 'Invalid request')
            continue
        ident, method = msg.get('id'), msg['method']
        if 'id' in msg and (type(ident) not in (int, str)):
            error(None, -32600, 'Invalid request id')
            continue
        params = msg.get('params', {})
        if not isinstance(params, dict):
            if 'id' in msg:
                error(ident, -32602, 'Parameters must be an object')
            continue
        if 'id' not in msg:
            if method == 'notifications/initialized' and initialized:
                ready = True
            continue
        if method == 'initialize':
            if initialized or not isinstance(params.get('protocolVersion'), str) or not isinstance(params.get('capabilities'), dict) or not isinstance(params.get('clientInfo'), dict):
                error(ident, -32602, 'Invalid initialization')
                continue
            initialized = True
            result = {'protocolVersion': PROTOCOL, 'capabilities': {'tools': {}},
                      'serverInfo': {'name': 'cortex-local', 'version': '0.4.0'},
                      'instructions': 'Use cortex_read/cortex_write on the explicitly configured board. Read document versions before mutations. No board is created automatically.'}
        elif method == 'ping':
            result = {}
        elif not ready:
            error(ident, -32002, 'Initialize the session first')
            continue
        elif method == 'tools/list':
            result = {'tools': tools}
        elif method == 'tools/call':
            name, args = params.get('name'), params.get('arguments', {})
            if not isinstance(name, str) or name not in {'cortex_read', 'cortex_write'}:
                error(ident, -32602, 'Unknown tool')
                continue
            try:
                if not isinstance(args, dict) or not isinstance(args.get('op'), str) or args.get('op') not in (READS if name == 'cortex_read' else WRITES):
                    raise LocalError('invalid_argument', 'Operation is not supported by this tool')
                data = store.dispatch(board, args)
                result = {'content': [{'type': 'text', 'text': encode(data)}], 'structuredContent': data, 'isError': False}
            except LocalError as err:
                result = {'content': [{'type': 'text', 'text': encode(err.as_dict())}], 'structuredContent': err.as_dict(), 'isError': True}
            except Exception:
                result = {'content': [{'type': 'text', 'text': 'Local operation failed'}], 'isError': True}
        else:
            error(ident, -32601, 'Method not found')
            continue
        send({'jsonrpc': '2.0', 'id': ident, 'result': result})
