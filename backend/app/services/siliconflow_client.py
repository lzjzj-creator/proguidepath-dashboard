import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

DEFAULT_TEXT_MODEL = "Qwen/Qwen2.5-72B-Instruct"
DEFAULT_LAYOUT_MODEL = "Qwen/Qwen3.6-Plus"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 45
DEFAULT_MAX_RETRIES = 0

logger = logging.getLogger(__name__)


def _backend_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read_env_file() -> Dict[str, str]:
    env_path = os.path.join(_backend_dir(), ".env")
    values: Dict[str, str] = {}
    try:
        with open(env_path, "r", encoding="utf-8") as file:
            for raw_line in file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return values


def _read_json_config() -> Dict[str, Any]:
    config_path = os.getenv("SILICONFLOW_CONFIG_PATH", "").strip() or os.path.join(
        _backend_dir(), "config", "siliconflow.json"
    )
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class SiliconFlowClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        allow_model_fallback: bool = True,
    ) -> None:
        env_file = _read_env_file()
        config = _read_json_config()

        self.api_key = (
            api_key
            or os.getenv("SILICONFLOW_API_KEY", "").strip()
            or env_file.get("SILICONFLOW_API_KEY")
            or config.get("apiKey")
            or config.get("api_key")
            or ""
        ).strip()
        self.base_url = (
            base_url
            or os.getenv("SILICONFLOW_BASE_URL", "").strip()
            or env_file.get("SILICONFLOW_BASE_URL")
            or config.get("baseUrl")
            or config.get("base_url")
            or "https://api.siliconflow.cn/v1"
        ).strip()
        self.model = (
            model
            or os.getenv("SILICONFLOW_MODEL", "").strip()
            or env_file.get("SILICONFLOW_MODEL")
            or config.get("model")
            or config.get("modelName")
            or DEFAULT_TEXT_MODEL
        ).strip()
        self.timeout_seconds = max(5, int(timeout_seconds))
        self.allow_model_fallback = allow_model_fallback

        if not self.api_key:
            raise RuntimeError("SILICONFLOW_API_KEY 未配置，请通过环境变量或配置文件设置。")

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        extra: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> str:
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra:
            payload.update(extra)

        request_timeout = max(5, int(timeout_seconds or self.timeout_seconds))
        retry_count = max(0, int(max_retries))
        last_error: Optional[RuntimeError] = None

        for model_name in self._candidate_models():
            payload["model"] = model_name
            response: Optional[requests.Response] = None
            should_try_next_model = False
            for attempt in range(retry_count + 1):
                logger.info(
                    "siliconflow_request_start model=%s timeout=%ss message_count=%s attempt=%s/%s",
                    model_name,
                    request_timeout,
                    len(messages),
                    attempt + 1,
                    retry_count + 1,
                )
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=(10, request_timeout))
                    break
                except requests.Timeout as exc:
                    error = RuntimeError(f"硅基流动请求超时: {exc}")
                    if attempt < retry_count:
                        last_error = error
                        logger.warning(
                            "siliconflow_request_retry_timeout model=%s attempt=%s/%s error=%s",
                            model_name,
                            attempt + 1,
                            retry_count + 1,
                            str(exc)[:200],
                        )
                        time.sleep(min(2.0, 0.5 * (attempt + 1)))
                        continue
                    if self._should_retry_with_fallback(None, str(exc), model_name):
                        last_error = error
                        should_try_next_model = True
                        break
                    raise error from exc
                except requests.RequestException as exc:
                    error = RuntimeError(f"硅基流动请求异常: {exc}")
                    if attempt < retry_count:
                        last_error = error
                        logger.warning(
                            "siliconflow_request_retry_exception model=%s attempt=%s/%s error=%s",
                            model_name,
                            attempt + 1,
                            retry_count + 1,
                            str(exc)[:200],
                        )
                        time.sleep(min(2.0, 0.5 * (attempt + 1)))
                        continue
                    if self._should_retry_with_fallback(None, str(exc), model_name):
                        last_error = error
                        should_try_next_model = True
                        break
                    raise error from exc
            if should_try_next_model or response is None:
                continue

            if not response.ok:
                response_text = ""
                try:
                    response_text = (response.text or "").strip()
                except Exception:
                    response_text = ""
                response_text = response_text[:5000]
                error = RuntimeError(
                    f"硅基流动返回错误: HTTP {response.status_code} {response.reason}; "
                    f"body={response_text or '(empty response)'}; model={model_name}"
                )
                if self._should_retry_with_fallback(response.status_code, response_text, model_name):
                    last_error = error
                    logger.warning(
                        "siliconflow_request_retry model=%s status=%s reason=%s",
                        model_name,
                        response.status_code,
                        response.reason,
                    )
                    continue
                raise error

            data = response.json()
            logger.info("siliconflow_request_done model=%s status=%s", model_name, response.status_code)

            try:
                return data["choices"][0]["message"]["content"]
            except Exception:
                for key in ["output_text", "text", "result"]:
                    if isinstance(data.get(key), str):
                        return data[key]
                raise RuntimeError(f"无法解析硅基流动响应: {data}")

        if last_error:
            raise last_error
        raise RuntimeError("硅基流动调用失败：未找到可用模型")

    def _candidate_models(self) -> List[str]:
        models = [self.model]
        if self.allow_model_fallback and self.model != DEFAULT_TEXT_MODEL:
            models.append(DEFAULT_TEXT_MODEL)
        return models

    def _should_retry_with_fallback(self, status_code: Optional[int], response_text: str, model_name: str) -> bool:
        if model_name == DEFAULT_TEXT_MODEL:
            return False

        lowered = (response_text or "").lower()
        if status_code in {403, 408, 429, 500, 502, 503, 504}:
            return True
        if "model disabled" in lowered or '"code":30003' in lowered:
            return True
        if "timeout" in lowered or "timed out" in lowered:
            return True
        return False


def extract_json_object(text: str) -> Any:
    cleaned = _strip_code_fences(text or "").strip()
    if not cleaned:
        raise ValueError("No JSON content found")

    direct = _try_load_json(cleaned)
    if isinstance(direct, dict):
        return direct

    decoder = json.JSONDecoder()
    for start in [index for index, char in enumerate(cleaned) if char == "{"]:
        try:
            parsed, _ = decoder.raw_decode(cleaned[start:])
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed

    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last != -1 and last > first:
        direct = _try_load_json(cleaned[first : last + 1])
        if isinstance(direct, dict):
            return direct

    raise ValueError("No parseable JSON object found")


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    stripped = stripped[3:]
    if stripped.startswith("json"):
        stripped = stripped[4:]
    end = stripped.rfind("```")
    if end != -1:
        stripped = stripped[:end]
    return stripped.strip()


def _try_load_json(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except Exception:
        return None


def create_resume_layout_client(
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    allow_model_fallback: bool = False,
) -> SiliconFlowClient:
    env_file = _read_env_file()
    config = _read_json_config()
    layout_config = config.get("resumeLayout") if isinstance(config.get("resumeLayout"), dict) else {}

    api_key = (
        os.getenv("RESUME_LAYOUT_API_KEY", "").strip()
        or env_file.get("RESUME_LAYOUT_API_KEY")
        or layout_config.get("apiKey")
        or layout_config.get("api_key")
        or config.get("resumeLayoutApiKey")
        or config.get("resume_layout_api_key")
        or os.getenv("SILICONFLOW_API_KEY", "").strip()
        or env_file.get("SILICONFLOW_API_KEY")
        or config.get("apiKey")
        or config.get("api_key")
        or ""
    ).strip()
    base_url = (
        os.getenv("RESUME_LAYOUT_BASE_URL", "").strip()
        or env_file.get("RESUME_LAYOUT_BASE_URL")
        or layout_config.get("baseUrl")
        or layout_config.get("base_url")
        or config.get("resumeLayoutBaseUrl")
        or config.get("resume_layout_base_url")
        or os.getenv("SILICONFLOW_BASE_URL", "").strip()
        or env_file.get("SILICONFLOW_BASE_URL")
        or config.get("baseUrl")
        or config.get("base_url")
        or "https://api.siliconflow.cn/v1"
    ).strip()
    model = (
        os.getenv("RESUME_LAYOUT_MODEL", "").strip()
        or env_file.get("RESUME_LAYOUT_MODEL")
        or layout_config.get("model")
        or layout_config.get("modelName")
        or config.get("resumeLayoutModel")
        or config.get("resume_layout_model")
        or DEFAULT_LAYOUT_MODEL
    ).strip()

    return SiliconFlowClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        allow_model_fallback=allow_model_fallback,
    )
