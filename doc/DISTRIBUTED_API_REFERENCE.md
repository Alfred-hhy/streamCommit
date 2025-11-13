# VDS 分布式 API 参考文档

## 📋 概述

本文档详细描述了 VDS 分布式系统的所有 REST API 端点、请求/响应格式、错误处理等。

---

## 🔧 通用约定

### 基础 URL

```
DO Server:       http://localhost:5001
SS Server:       http://localhost:5002
Verifier Server: http://localhost:5003
```

### 请求格式

- **Content-Type**: `application/json`
- **编码**: UTF-8
- **序列化**: Charm 对象使用 Base64 编码

### 响应格式

**成功响应**:
```json
{
  "status": "success",
  "data": { ... }
}
```

**错误响应**:
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": { ... }
  }
}
```

### 错误代码

| 代码 | 含义 | HTTP 状态码 |
|------|------|------------|
| `INVALID_REQUEST` | 请求格式错误 | 400 |
| `MISSING_PARAMETER` | 缺少必需参数 | 400 |
| `INVALID_PARAMETER` | 参数值无效 | 400 |
| `NOT_INITIALIZED` | 系统未初始化 | 500 |
| `BATCH_NOT_FOUND` | 批次不存在 | 404 |
| `VERIFICATION_FAILED` | 验证失败 | 400 |
| `INTERNAL_ERROR` | 内部错误 | 500 |

---

## 🏢 DO Server API (Port 5001)

### 1. 健康检查

**端点**: `GET /health`

**描述**: 检查服务器是否正常运行

**请求**: 无

**响应**:
```json
{
  "status": "ok",
  "timestamp": 1699876543
}
```

---

### 2. 初始化系统

**端点**: `POST /init`

**描述**: 初始化 VDS 系统，生成 CRS 和密钥

**请求**:
```json
{
  "n": 8,
  "curve": "MNT224"
}
```

**参数**:
- `n` (int, 必需): 向量大小
- `curve` (string, 可选): 椭圆曲线类型，默认 "MNT224"

**响应**:
```json
{
  "status": "success",
  "data": {
    "crs": {
      "n": 8,
      "g": "<base64_encoded_G1>",
      "g_hat": "<base64_encoded_G2>",
      "g_list": ["<base64>", "<base64>", ...],
      "g_hat_list": ["<base64>", "<base64>", ...]
    },
    "global_pk": {
      "vk_sig": "<base64_encoded_ecdsa_vk>",
      "acc_pk": {
        "g": "<base64_encoded_G1>",
        "g_hat": "<base64_encoded_G2>",
        "g_hat_s": "<base64_encoded_G2>"
      },
      "f_current": "<base64_encoded_G1>"
    },
    "server_keys": {
      "g_s_list": ["<base64>", "<base64>", ...]
    }
  }
}
```

---

### 3. 创建批次

**端点**: `POST /create_batch`

**描述**: 创建新的数据批次

**请求**:
```json
{
  "m_matrix": [
    ["<base64_ZR>", "<base64_ZR>", ...],
    ["<base64_ZR>", "<base64_ZR>", ...]
  ],
  "t_vector": ["<base64_ZR>", "<base64_ZR>", ...]
}
```

**参数**:
- `m_matrix` (array, 必需): 数据矩阵（多列）
  - 外层数组：列
  - 内层数组：时间点的数据值
- `t_vector` (array, 必需): 时间向量

**响应**:
```json
{
  "status": "success",
  "data": {
    "batch_id": "a1b2c3d4e5f6g7h8",
    "header": {
      "C_data_list": ["<base64_G1>", "<base64_G1>", ...],
      "C_time": "<base64_G2>",
      "sigma": "<base64_bytes>"
    },
    "secrets": {
      "m_matrix": [
        ["<base64_ZR>", ...],
        ["<base64_ZR>", ...]
      ],
      "t": ["<base64_ZR>", ...],
      "gamma_data_list": ["<base64_ZR>", ...],
      "gamma_time": "<base64_ZR>"
    }
  }
}
```

---

### 4. 撤销批次

**端点**: `POST /revoke_batch`

**描述**: 撤销指定批次

**请求**:
```json
{
  "sigma": "<base64_bytes>"
}
```

**参数**:
- `sigma` (string, 必需): 要撤销的批次签名（Base64 编码）

**响应**:
```json
{
  "status": "success",
  "data": {
    "g_s_q_new": "<base64_G1>",
    "new_global_pk": {
      "vk_sig": "<base64>",
      "acc_pk": { ... },
      "f_current": "<base64_G1>"
    },
    "sigma_bytes": "<base64_bytes>"
  }
}
```

---

### 5. 更新批次

**端点**: `POST /update_batch`

**描述**: 更新批次（撤销旧批次 + 创建新批次）

**请求**:
```json
{
  "old_header": {
    "C_data_list": ["<base64_G1>", ...],
    "C_time": "<base64_G2>",
    "sigma": "<base64_bytes>"
  },
  "new_m_matrix": [
    ["<base64_ZR>", ...],
    ["<base64_ZR>", ...]
  ],
  "new_t_vector": ["<base64_ZR>", ...]
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "g_s_q_new": "<base64_G1>",
    "new_global_pk": { ... },
    "sigma_bytes": "<base64_bytes>",
    "new_batch_id": "x1y2z3...",
    "new_header": { ... },
    "new_secrets": { ... }
  }
}
```

---

## 🗄️ SS Server API (Port 5002)

### 1. 健康检查

**端点**: `GET /health`

**响应**: 同 DO Server

---

### 2. 初始化存储

**端点**: `POST /init`

**请求**:
```json
{
  "crs": { ... },
  "server_keys": { ... }
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "message": "Storage Server initialized"
  }
}
```

---

### 3. 存储批次

**端点**: `POST /store_batch`

**请求**:
```json
{
  "batch_id": "a1b2c3d4...",
  "header": { ... },
  "secrets": { ... }
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "message": "Batch stored successfully",
    "batch_id": "a1b2c3d4..."
  }
}
```

---

### 4. 生成 DC 证明

**端点**: `POST /generate_dc_proof`

**请求**:
```json
{
  "batch_id": "a1b2c3d4...",
  "t_query": ["<base64_ZR>", "<base64_ZR>", ...],
  "column_index": 0
}
```

**参数**:
- `batch_id` (string, 必需): 批次 ID
- `t_query` (array, 必需): 查询向量
- `column_index` (int, 可选): 列索引，默认 0

**响应**:
```json
{
  "status": "success",
  "data": {
    "proof": {
      "pi_agg": "<base64>",
      "pi_non": "<base64>",
      "C_y": "<base64_G1>",
      "pi_y": "<base64>",
      "pi_x": "<base64>"
    },
    "result": "<base64_ZR>",
    "header": { ... }
  }
}
```

---

### 5. 生成 DA 证明

**端点**: `POST /generate_da_proof`

**请求**:
```json
{
  "batch_id": "a1b2c3d4...",
  "column_index": 0
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "proof": {
      "pi_agg": "<base64>",
      "pi_non": "<base64>",
      "C_y": "<base64_G1>",
      "pi_y": "<base64>",
      "pi_x": "<base64>",
      "challenge": "<base64_ZR>"
    },
    "header": { ... }
  }
}
```

---

## ✅ Verifier Server API (Port 5003)

### 1. 健康检查

**端点**: `GET /health`

**响应**: 同 DO Server

---

### 2. 初始化验证器

**端点**: `POST /init`

**请求**:
```json
{
  "crs": { ... },
  "global_pk": { ... }
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "message": "Verifier initialized"
  }
}
```

---

### 3. 验证 DC 查询

**端点**: `POST /verify_dc_query`

**请求**:
```json
{
  "header": { ... },
  "proof": { ... },
  "result": "<base64_ZR>",
  "t_query": ["<base64_ZR>", ...],
  "column_index": 0
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "is_valid": true,
    "verification_time": 0.0234
  }
}
```

---

### 4. 验证 DA 审计

**端点**: `POST /verify_da_audit`

**请求**:
```json
{
  "header": { ... },
  "proof": { ... },
  "column_index": 0
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "is_valid": true,
    "verification_time": 0.0456
  }
}
```

---

### 5. 更新全局公钥

**端点**: `POST /update_global_pk`

**请求**:
```json
{
  "new_global_pk": { ... }
}
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "message": "Global public key updated"
  }
}
```


