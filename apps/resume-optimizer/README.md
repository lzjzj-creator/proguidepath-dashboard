# Recruitment Matching Frontend

Vue 3 + Vite 招聘工作台，用于演示 `AI+招聘` 赛道闭环：

1. 输入岗位 JD 或选择示例岗位。
2. 批量上传 PDF 简历。
3. 查看候选人匹配分、推荐状态、证据解释、风险点和面试问题。

## 运行

```bash
cd frontend
npm install
npm run dev
```

默认后端地址为 `http://localhost:8000`。如需修改：

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## 构建

```bash
npm run build
```
