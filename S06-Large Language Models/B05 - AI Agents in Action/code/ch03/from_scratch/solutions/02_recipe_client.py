# Problem 02 -- exercise every primitive, then tour how each one fails.

import asyncio
import sys
import json
from pathlib import Path

from mcp import MCPError, StdioServerParameters
from mcp.client import Client

SERVER_PATH = Path(__file__).parent / "02_recipe_server.py"


async def main() -> None:
    server_params = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])

    async with Client(server_params) as client:
        # your turn: list_resources() and list_resource_templates(), print both

        # your turn: read_resource("recipes://index"), then read one real recipe

        # your turn: get_prompt("cook_with", {"ingredient": "egg", "max_minutes": "15"})
        # print each message's role and text

        # your turn: the failure tour -- one call per failure:
        #   search_recipes('') -> is_error, print text
        #   broken_tool() -> is_error, print text
        #   no_such_tool() -> is_error, print text
        #   read_resource("recipes://unknown") -> catch MCPError, print code
        #   get_prompt("cook_with", max_minutes="2") -> catch MCPError, print code + message
        print("--------- resource vs template ------------")
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        print(f"  fixed resources : {[r.uri for r in resources.resources]}")
        print(f"  templates       : {[t.uri_template for t in templates.resource_templates]}")

        print("\n--- reading resources ---")
        index_text = await client.read_resource("recipes://index")
        print(f"  recipes://index ->\n{index_text.contents[0].text}")

        first_name = index_text.contents[0].text.splitlines()[0]
        recipe_text = await client.read_resource(f"recipes://{first_name}")
        print(f"\n  recipes://{first_name} ->\n{recipe_text.contents[0].text}")

        print("\n--- getting a prompt ---")
        prompt_result = await client.get_prompt(
            "cook_with", {"ingredient": "egg", "max_minutes": "15"}
        )
        for message in prompt_result.messages:
            print(f"  [{message.role}] {message.content.text}")

        # calling a tool
        print("\n--- calling mcp tool ---")
        result = await client.call_tool("search_recipes", {"cuisine" : "french"})
        print("returned recipe is : \n")
        print(json.dumps(result.structured_content, indent=4))

        print("\n--- failure tour ---")
        result = await client.call_tool("search_recipes", {"cuisine": ""})
        print(f"  tool  search_recipes('')  -> is_error={result.is_error}  text={result.content[0].text!r}")

        result = await client.call_tool("broken_tool", {})
        print(f"  tool  broken_tool()       -> is_error={result.is_error}  text={result.content[0].text!r}")

        result = await client.call_tool("no_such_tool", {})
        print(f"  tool  no_such_tool()      -> is_error={result.is_error}  text={result.content[0].text!r}")

        try:
            await client.read_resource("recipes://unknown")
        except MCPError as error:
            print(f"  res   recipes://unknown   -> MCPError code={error.code}")

        try:
            await client.get_prompt("cook_with", {"ingredient": "egg", "max_minutes": "2"})
        except MCPError as error:
            print(f"  prompt cook_with(max=2)   -> MCPError code={error.code} {error.message!r}")


if __name__ == "__main__":
    asyncio.run(main())

# Got this output in terminal

# --------- resource vs template ------------
#   fixed resources : ['recipes://index']
#   templates       : ['recipes://{name}']

# --- reading resources ---
#   recipes://index ->
# omelette
# pasta aglio e olio
# masala chai
# ratatouille

#   recipes://omelette ->
# omelette (french, 10 min)
# ingredients: eggs, butter, salt
# steps:
#   1. beat the eggs
#   2. melt butter in a pan
#   3. pour and fold

# --- getting a prompt ---
#   [user] Suggest a recipe that uses egg and takes at most 15 minutes to cook

# --- calling mcp tool ---
# [MCP tool call] : search_recipes for cuisinefrench -> ['omelette', 'ratatouille']
# returned recipe is : 

# {
#     "result": [
#         "omelette",
#         "ratatouille"
#     ]
# }

# --- failure tour ---
# [10/06/26 13:10:51] INFO     Tool 'search_recipes' failed: 'Error executing tool search_recipes: cuisine cannot be empty'               server.py:438
#   tool  search_recipes('')  -> is_error=True  text='Error executing tool search_recipes: cuisine cannot be empty'
#                     ERROR    Tool 'broken_tool' raised an unexpected exception                                                          server.py:440
#                              ╭────────────────────────────────── Traceback (most recent call last) ───────────────────────────────────╮              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/server/mcpser │              
#                              │ ver/tools/base.py:176 in run                                                                           │              
#                              │                                                                                                        │              
#                              │   173 │   │   │   │   │   return self.fn_metadata.convert_result(resolved) if convert_result           │              
#                              │       else resolved                                                                                    │              
#                              │   174 │   │   │   │   pass_directly |= resolved                                                        │              
#                              │   175 │   │   │                                                                                        │              
#                              │ ❱ 176 │   │   │   result = await self.fn_metadata.call_fn(self.fn, self.is_async, validated,           │              
#                              │       pass_directly)                                                                                   │              
#                              │   177 │   │   │                                                                                        │              
#                              │   178 │   │   │   # Registration rejects the annotated form of this combination; this covers           │              
#                              │   179 │   │   │   # a body that returns an InputRequiredResult without declaring it. It is             │              
#                              │                                                                                                        │              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/server/mcpser │              
#                              │ ver/utilities/func_metadata.py:164 in call_fn                                                          │              
#                              │                                                                                                        │              
#                              │   161 │   │   kwargs = arguments | (arguments_to_pass_directly or {})                                  │              
#                              │   162 │   │   if fn_is_async:                                                                          │              
#                              │   163 │   │   │   return await fn(**kwargs)                                                            │              
#                              │ ❱ 164 │   │   return await anyio.to_thread.run_sync(functools.partial(fn, **kwargs))                   │              
#                              │   165 │                                                                                                │              
#                              │   166 │   @deprecated(                                                                                 │              
#                              │   167 │   │   "FuncMetadata.call_fn_with_arg_validation() is deprecated and will be removed in         │              
#                              │       3.0; "                                                                                           │              
#                              │                                                                                                        │              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/anyio/to_thread.p │              
#                              │ y:65 in run_sync                                                                                       │              
#                              │                                                                                                        │              
#                              │   62 │   │   │   stacklevel=2,                                                                         │              
#                              │   63 │   │   )                                                                                         │              
#                              │   64 │                                                                                                 │              
#                              │ ❱ 65 │   return await get_async_backend().run_sync_in_worker_thread(                                   │              
#                              │   66 │   │   func, args, abandon_on_cancel=abandon_on_cancel, limiter=limiter                          │              
#                              │   67 │   )                                                                                             │              
#                              │   68                                                                                                   │              
#                              │                                                                                                        │              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/anyio/_backends/_ │              
#                              │ asyncio.py:2641 in run_sync_in_worker_thread                                                           │              
#                              │                                                                                                        │              
#                              │   2638 │   │   │   │   │   worker_scope = scope._parent_scope                                          │              
#                              │   2639 │   │   │   │                                                                                   │              
#                              │   2640 │   │   │   │   worker.queue.put_nowait((context, func, args, future, worker_scope))            │              
#                              │ ❱ 2641 │   │   │   │   return await future                                                             │              
#                              │   2642 │                                                                                               │              
#                              │   2643 │   @classmethod                                                                                │              
#                              │   2644 │   def check_cancelled(cls) -> None:                                                           │              
#                              │                                                                                                        │              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/anyio/_backends/_ │              
#                              │ asyncio.py:1033 in run                                                                                 │              
#                              │                                                                                                        │              
#                              │   1030 │   │   │   │   │   exception: BaseException | None = None                                      │              
#                              │   1031 │   │   │   │   │   threadlocals.current_cancel_scope = cancel_scope                            │              
#                              │   1032 │   │   │   │   │   try:                                                                        │              
#                              │ ❱ 1033 │   │   │   │   │   │   result = context.run(func, *args)                                       │              
#                              │   1034 │   │   │   │   │   except BaseException as exc:                                                │              
#                              │   1035 │   │   │   │   │   │   exception = exc                                                         │              
#                              │   1036 │   │   │   │   │   finally:                                                                    │              
#                              │                                                                                                        │              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/S06-Large Language Models/B05 - AI Agents in         │              
#                              │ Action/code/ch03/from_scratch/solutions/02_recipe_server.py:56 in broken_tool                          │              
#                              │                                                                                                        │              
#                              │    53 def broken_tool() -> str:                                                                        │              
#                              │    54 │   """A tool that always crashes, to see what a client gets from an unplanned error."""         │              
#                              │    55 │   # your turn: raise a plain ValueError                                                        │              
#                              │ ❱  56 │   raise ValueError("secret internal detail")                                                   │              
#                              │    57                                                                                                  │              
#                              │    58                                                                                                  │              
#                              │    59 @mcp.resource("recipes://index")                                                                 │              
#                              ╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯              
#                              ValueError: secret internal detail                                                                                      
                                                                                                                                                     
#                              The above exception was the direct cause of the following exception:                                                    
                                                                                                                                                     
#                              ╭────────────────────────────────── Traceback (most recent call last) ───────────────────────────────────╮              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/server/mcpser │              
#                              │ ver/server.py:427 in _handle_call_tool                                                                 │              
#                              │                                                                                                        │              
#                              │    424 │   ) -> CallToolResult | InputRequiredResult:                                                  │              
#                              │    425 │   │   context = Context(request_context=ctx, mcp_server=self, input_params=params,            │              
#                              │        subscriptions=self._subscriptions)                                                              │              
#                              │    426 │   │   try:                                                                                    │              
#                              │ ❱  427 │   │   │   return await self.call_tool(params.name, params.arguments or {}, context)           │              
#                              │    428 │   │   except MCPError:                                                                        │              
#                              │    429 │   │   │   raise                                                                               │              
#                              │    430 │   │   except Exception as exc:                                                                │              
#                              │                                                                                                        │              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/server/mcpser │              
#                              │ ver/server.py:533 in call_tool                                                                         │              
#                              │                                                                                                        │              
#                              │    530 │   │   """                                                                                     │              
#                              │    531 │   │   if context is None:                                                                     │              
#                              │    532 │   │   │   context = Context(mcp_server=self, subscriptions=self._subscriptions)               │              
#                              │ ❱  533 │   │   return await self._tool_manager.call_tool(name, arguments, context,                     │              
#                              │        convert_result=True)                                                                            │              
#                              │    534 │                                                                                               │              
#                              │    535 │   async def list_resources(self) -> list[MCPResource]:                                        │              
#                              │    536 │   │   """List all available resources."""                                                     │              
#                              │                                                                                                        │              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/server/mcpser │              
#                              │ ver/tools/tool_manager.py:87 in call_tool                                                              │              
#                              │                                                                                                        │              
#                              │   84 │   │   if not tool:                                                                              │              
#                              │   85 │   │   │   raise ToolError(f"Unknown tool: {name}")                                              │              
#                              │   86 │   │                                                                                             │              
#                              │ ❱ 87 │   │   return await tool.run(arguments, context, convert_result=convert_result)                  │              
#                              │   88                                                                                                   │              
#                              │                                                                                                        │              
#                              │ /Users/gkmit/Desktop/dev/others/ai/WebDevLearning/.venv/lib/python3.12/site-packages/mcp/server/mcpser │              
#                              │ ver/tools/base.py:210 in run                                                                           │              
#                              │                                                                                                        │              
#                              │   207 │   │   │   raise ToolError(f"Error executing tool {self.name}: {exc}") from exc                 │              
#                              │   208 │   │   except Exception as exc:                                                                 │              
#                              │   209 │   │   │   # A crash: the exception's own text stays on the server.                             │              
#                              │ ❱ 210 │   │   │   raise UnexpectedToolError(f"Error executing tool {self.name}") from exc              │              
#                              │   211                                                                                                  │              
#                              ╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯              
#                              UnexpectedToolError: Error executing tool broken_tool                                                                   
#   tool  broken_tool()       -> is_error=True  text='Error executing tool broken_tool'
#                     INFO     Tool 'no_such_tool' failed: 'Unknown tool: no_such_tool'                                                   server.py:438
#   tool  no_such_tool()      -> is_error=True  text='Unknown tool: no_such_tool'
#                     INFO     Resource 'recipes://unknown' failed: "no recipe named 'unknown'"                                           server.py:458
#   res   recipes://unknown   -> MCPError code=-32602
#   prompt cook_with(max=2)   -> MCPError code=-32602 'max_minutes must be at least 5'
