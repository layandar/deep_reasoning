
import os
import json
import asyncio

from dotenv import load_dotenv
from openai import OpenAI

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is not set. "
        "Add it to your .env file."
    )

MCP_URL = "http://127.0.0.1:8765/mcp"

# Change this to the OpenRouter model you want to use.
MODEL = "deepseek/deepseek-chat-v3.1"

# ============================================================
# OPENROUTER CLIENT
# ============================================================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a deep-reasoning procurement agent specialized in supplier
discovery and quotation analysis.

Your task is to analyze the quotation provided by the user and identify
the best supplier based on the requirements in the quotation.

You have access to web research tools through Hound.

IMPORTANT:
You MUST use the Hound web research tools before making your final
supplier recommendation.

Use your existing knowledge along with hound.

You should investigate multiple potential suppliers whenever possible.

Your process should be:

1. Extract the requirements from the quotation.

2. Identify the important criteria, including:
   - Product/material
   - Quantity
   - Technical specifications
   - Quality requirements
   - Certifications
   - Standards
   - Delivery requirements
   - Geographic requirements
   - Budget or price requirements
   - Any other supplier requirements

3. Search the web for multiple potential suppliers.

4. Investigate each promising supplier.

5. Compare the suppliers against the quotation requirements.

6. Select the best supplier based on the available evidence.

Choose the supplier that best meets all the requirements and has the most verified information.

Do NOT invent:
- prices
- certifications
- stock availability
- quantities
- delivery times
- product specifications

If information cannot be verified, explicitly state:
"Not verified."

Distinguish between:
- Information confirmed by the supplier
- Information from a third-party source
- Information inferred from available evidence
- Information that could not be verified

Prefer these sources, in order:

1. Official supplier websites
2. Manufacturer product pages
3. Official product catalogs and datasheets
4. Certification databases
5. Government sources
6. Reputable industry directories
7. Other reliable sources

Try to investigate at least 3 suppliers when enough candidates exist.

Your final response MUST contain:

## 1. Quotation Requirements

Summarize the requirements extracted from the quotation.

## 2. Suppliers Investigated

Provide a comparison table containing:

| Supplier | Product Match | Specifications | Quantity | Certifications | Price | Delivery | Evidence | Overall Assessment |

Use "Not verified" when information is unavailable.

## 3. Recommended Supplier

Identify the best supplier.

Explain why it is the best match and connect the reasoning directly
to the quotation requirements.

## 4. Evidence and Sources

For every important factual claim, identify the source used.

Include:
- Source name
- Website
- URL when available

## 5. Risks / Unverified Information

Clearly identify information that should be confirmed directly
with the supplier.

Examples:
- Current price
- Current stock
- Lead time
- Shipping cost
- Exact quantity
- Certification validity
- Customization
- Payment terms

## 6. Final Recommendation

Use this format:

Recommendation: [Supplier]

Confidence: High / Medium / Low

Reason:
[2-4 sentences explaining why this supplier is the strongest
candidate based on the evidence.]

The goal is not merely to find a supplier.

The goal is to determine which supplier is the BEST-SUPPORTED match
for the quotation using current web evidence.
"""


# ============================================================
# MCP → OPENAI TOOL FORMAT
# ============================================================

def convert_mcp_tool_to_openai(tool):
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema
        }
    }


# ============================================================
# EXTRACT MCP RESULT TEXT
# ============================================================

def extract_tool_result(result):

    output = []

    if not result or not result.content:
        return "No result returned by the tool."

    for content in result.content:

        if hasattr(content, "text") and content.text:
            output.append(content.text)

        elif hasattr(content, "data") and content.data:
            output.append(str(content.data))

        else:
            output.append(str(content))

    return "\n".join(output)


# ============================================================
# RUN SUPPLIER AGENT
# ============================================================

async def run_agent(quotation):

    print("\nConnecting to Hound...")
    print(f"MCP server: {MCP_URL}")

    async with streamable_http_client(MCP_URL) as (
        read_stream,
        write_stream,
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            print("Initializing MCP session...")

            await session.initialize()

            print("Getting Hound tools...")

            tools_result = await session.list_tools()

            mcp_tools = tools_result.tools

            print("\nAvailable Hound tools:")

            for tool in mcp_tools:
                print(f"  - {tool.name}")

            openrouter_tools = [
                convert_mcp_tool_to_openai(tool)
                for tool in mcp_tools
            ]

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"""
Analyze the following quotation and find the best supplier.

QUOTATION:

{quotation}
"""
                }
            ]

            print("\nStarting supplier research...\n")

            # ====================================================
            # AGENT LOOP
            # ====================================================

            while True:

                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=openrouter_tools,
                    tool_choice="auto"
                )

                message = response.choices[0].message

                # ------------------------------------------------
                # No tool call = final answer
                # ------------------------------------------------

                if not message.tool_calls:

                    messages.append(
                        {
                            "role": "assistant",
                            "content": message.content or ""
                        }
                    )

                    print("\n")
                    print("=" * 80)
                    print("FINAL SUPPLIER RECOMMENDATION")
                    print("=" * 80)
                    print("\n")
                    print(message.content)

                    break

                # ------------------------------------------------
                # Add assistant tool calls to conversation
                # ------------------------------------------------

                assistant_message = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": []
                }

                for tool_call in message.tool_calls:

                    assistant_message["tool_calls"].append(
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                    )

                messages.append(assistant_message)

                # ------------------------------------------------
                # Execute Hound tools
                # ------------------------------------------------

                for tool_call in message.tool_calls:

                    tool_name = tool_call.function.name
                    arguments_string = tool_call.function.arguments

                    print("\n" + "-" * 80)
                    print(f"HOUND TOOL: {tool_name}")
                    print(f"ARGUMENTS: {arguments_string}")
                    print("-" * 80)

                    try:

                        arguments = json.loads(arguments_string)

                    except json.JSONDecodeError:

                        arguments = {}

                    try:

                        result = await session.call_tool(
                            tool_name,
                            arguments=arguments
                        )

                        tool_output = extract_tool_result(result)

                    except Exception as e:

                        tool_output = (
                            f"Hound tool execution failed: {type(e).__name__}: {e}"
                        )

                    print("\nHound result received.")

                    # ------------------------------------------------
                    # Send Hound result back to OpenRouter
                    # ------------------------------------------------

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_output
                        }
                    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 80)
    print("DEEP REASONING SUPPLIER AGENT")
    print("=" * 80)

    quotation = input(
        "\nPaste your quotation here:\n\n"
    )

    if not quotation.strip():
        print("No quotation provided.")
        return

    await run_agent(quotation)


if __name__ == "__main__":
    asyncio.run(main())

