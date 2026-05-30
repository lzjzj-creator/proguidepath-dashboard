"use client";

import { useState } from "react";

type AiConfigPanelProps = {
  onTestConnection: () => void;
  testing: boolean;
};

export function AiConfigPanel({ onTestConnection, testing }: AiConfigPanelProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-4 rounded-[24px] border border-sky-100 bg-white">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-slate-700"
      >
        <span>AI 服务状态</span>
        <span className={`transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="space-y-3 border-t border-sky-100 px-4 py-4">
          <div className="text-sm text-slate-600">
            <p className="leading-7">API 连接由服务端统一配置，使用环境变量中的密钥。</p>
            <p className="leading-7">模型: {process.env.NEXT_PUBLIC_APP_MODEL_HINT ?? "Qwen / fallback"}</p>
          </div>
          <button
            type="button"
            onClick={onTestConnection}
            disabled={testing}
            className="rounded-full border border-sky-100 px-4 py-2 text-xs text-slate-600 transition hover:border-blue-600"
          >
            {testing ? "测试中..." : "测试连接"}
          </button>
        </div>
      )}
    </div>
  );
}
