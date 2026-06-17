import json
import numpy as np
import faiss
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vector_store"))

index = faiss.read_index(os.path.join(BASE_PATH, "index.faiss"))
with open(os.path.join(BASE_PATH, "texts.json"), "r", encoding="utf-8") as f:
    texts = json.load(f)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"]
)

# ──────────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────────

def search_docs(query: str, k: int = 5) -> str:
    res = client.embeddings.create(
        model="nvidia/nv-embedqa-e5-v5",
        input=[query],
        encoding_format="float",
        extra_body={"input_type": "query", "truncate": "END"}
    )
    vec = np.array([res.data[0].embedding], dtype="float32")
    _, indices = index.search(vec, k)
    results = [texts[i] for i in indices[0] if i < len(texts)]
    return "\n\n---\n\n".join(results)


def search_docs_with_sources(query: str, k: int = 5) -> tuple[str, list[str]]:
    """搜尋文件並回傳來源預覽"""
    res = client.embeddings.create(
        model="nvidia/nv-embedqa-e5-v5",
        input=[query],
        encoding_format="float",
        extra_body={"input_type": "query", "truncate": "END"}
    )
    vec = np.array([res.data[0].embedding], dtype="float32")
    _, indices = index.search(vec, k)

    results = []
    sources = []
    for i in indices[0]:
        if i < len(texts):
            results.append(texts[i])
            preview = texts[i][:80].strip().replace("\n", " ")
            sources.append(preview)

    return "\n\n---\n\n".join(results), sources


def generate_code(description: str, stm32_model: str = "STM32F103") -> str:
    res = client.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[{
            "role": "user",
            "content": (
                f"Generate {stm32_model} HAL C code for: {description}\n"
                "Only output the code block, no explanation."
            )
        }],
        temperature=0.1,
        max_tokens=1024
    )
    return res.choices[0].message.content


def explain_register(register_name: str) -> str:
    context = search_docs(f"{register_name} register STM32 bits configuration")
    res = client.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[{
            "role": "user",
            "content": (
                f"Explain the STM32 {register_name} register in detail, "
                f"including all bits.\n\nContext from docs:\n{context}"
            )
        }],
        temperature=0.1,
        max_tokens=1024
    )
    return res.choices[0].message.content


# ──────────────────────────────────────────────
# 周邊資料表（依 STM32 系列分類，非窮舉，足供 agent 參考）
# ──────────────────────────────────────────────

PERIPHERALS_DB = {
    "STM32F0": {
        "core": "ARM Cortex-M0", "max_freq": "48 MHz",
        "peripherals": ["GPIO", "USART x2-4", "SPI x1-2", "I2C x1-2",
                         "ADC 12-bit", "TIM (basic/general)", "DMA",
                         "RTC", "IWDG/WWDG", "USB Device (some variants)"]
    },
    "STM32F103": {
        "core": "ARM Cortex-M3", "max_freq": "72 MHz",
        "peripherals": ["GPIO", "USART/UART x3-5", "SPI x2-3", "I2C x2",
                         "ADC 12-bit x2-3", "TIM1-8 (advanced/general/basic)",
                         "DMA x2", "CAN", "USB Device (FS)", "RTC", "IWDG/WWDG", "CRC"]
    },
    "STM32F3": {
        "core": "ARM Cortex-M4F (FPU)", "max_freq": "72 MHz",
        "peripherals": ["GPIO", "USART x3-5", "SPI x2-4", "I2C x2-3",
                         "ADC 12-bit (fast, op-amp integrated)", "Comparator",
                         "TIM (advanced/general/basic)", "DMA x2", "CAN",
                         "USB Device", "DAC", "RTC"]
    },
    "STM32F401": {
        "core": "ARM Cortex-M4F (FPU)", "max_freq": "84 MHz",
        "peripherals": ["GPIO", "USART x3", "SPI x4", "I2C x3",
                         "ADC 12-bit", "TIM1-14", "DMA x2", "USB OTG FS",
                         "RTC", "IWDG/WWDG", "CRC"]
    },
    "STM32F407": {
        "core": "ARM Cortex-M4F (FPU)", "max_freq": "168 MHz",
        "peripherals": ["GPIO", "USART/UART x6", "SPI x3", "I2C x3",
                         "ADC 12-bit x3", "DAC x2", "TIM1-14",
                         "DMA x2 (16 streams)", "CAN x2", "Ethernet MAC",
                         "USB OTG FS/HS", "SDIO", "RTC", "CRC"]
    },
    "STM32L4": {
        "core": "ARM Cortex-M4F (FPU, 超低功耗)", "max_freq": "80 MHz",
        "peripherals": ["GPIO", "USART/UART x3-6", "SPI x3", "I2C x4",
                         "ADC 12-bit x3", "DAC x2", "TIM (advanced/general/basic)",
                         "DMA x2", "CAN", "USB OTG FS", "SDMMC",
                         "RTC", "AES/HASH (安全)", "LPUART/LPTIM (低功耗)"]
    },
    "STM32H7": {
        "core": "ARM Cortex-M7 (雙核心型號含 M4)", "max_freq": "480 MHz",
        "peripherals": ["GPIO", "USART/UART x8", "SPI x6", "I2C x4",
                         "ADC 16-bit x3", "DAC x2", "TIM (advanced/general/basic) x14+",
                         "DMA + MDMA + BDMA", "CAN FD x2", "Ethernet MAC",
                         "USB OTG FS/HS", "SDMMC x2", "RTC", "Crypto/Hash 加速器",
                         "JPEG codec（部分型號）"]
    },
}


def list_peripherals(stm32_model: str = "STM32F103") -> str:
    """列出指定 STM32 系列的核心資訊與主要周邊清單"""
    # 嘗試完全比對，再嘗試前綴比對（例如 STM32F103C8T6 -> STM32F103）
    key = stm32_model.strip().upper()
    entry = PERIPHERALS_DB.get(key)

    if entry is None:
        for db_key in PERIPHERALS_DB:
            if key.startswith(db_key.upper()):
                entry = PERIPHERALS_DB[db_key]
                key = db_key
                break

    if entry is None:
        available = ", ".join(PERIPHERALS_DB.keys())
        return (
            f"找不到 '{stm32_model}' 的周邊資料。"
            f"目前資料庫支援的系列：{available}"
        )

    lines = [
        f"## {key} 周邊總覽",
        f"- 核心：{entry['core']}",
        f"- 最高時脈：{entry['max_freq']}",
        "- 主要周邊：",
    ]
    lines += [f"  - {p}" for p in entry["peripherals"]]
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Tool registry（供 agent dispatcher 使用）
# ──────────────────────────────────────────────

TOOLS = {
    "search_docs": search_docs,
    "generate_code": generate_code,
    "explain_register": explain_register,
    "list_peripherals": list_peripherals,
}

# ──────────────────────────────────────────────
# Tool schema（OpenAI function calling 格式）
# ──────────────────────────────────────────────

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": (
                "Search the STM32 reference manual and datasheet for relevant context. "
                "Use this before answering any register or peripheral question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query, e.g. 'UART baud rate register STM32F103'"
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of document chunks to retrieve (default 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_code",
            "description": (
                "Generate STM32 HAL C code for a given feature or peripheral description. "
                "Call this when the user wants working code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What the code should do, e.g. 'configure UART2 at 115200 baud with DMA TX'"
                    },
                    "stm32_model": {
                        "type": "string",
                        "description": "Target STM32 model, e.g. STM32F103, STM32H743",
                        "default": "STM32F103"
                    }
                },
                "required": ["description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explain_register",
            "description": (
                "Explain an STM32 hardware register in detail, including all bit fields "
                "and their meaning. Use this when the user asks about a specific register."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "register_name": {
                        "type": "string",
                        "description": "Register name, e.g. USART_CR1, RCC_APB1ENR, TIM_CR1"
                    }
                },
                "required": ["register_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_peripherals",
            "description": (
                "List the core specs and main on-chip peripherals (UART, SPI, I2C, ADC, "
                "TIM, DMA, etc.) available on a given STM32 series. Use this when the user "
                "asks what peripherals/features a chip has, or wants to compare series before "
                "choosing one."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stm32_model": {
                        "type": "string",
                        "description": "Target STM32 model or series, e.g. STM32F103, STM32H743",
                        "default": "STM32F103"
                    }
                },
                "required": []
            }
        }
    }
]