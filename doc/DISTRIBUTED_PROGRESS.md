# 分布式VDS开发进度

## 已完成的工作

### Phase 1: 本地多进程 + HTTP (✅ 已完成)

#### 1. 核心模块开发 ✅
- **distributed/serialization.py**: Charm群元素的序列化/反序列化工具
  - 支持G1, G2, ZR元素的base64序列化
  - 支持CRS, global_pk, batch header等复杂结构的序列化
  - **修复了单位元序列化问题**：G1/G2的单位元使用特殊标记而非直接序列化
  - 支持DEV_MODE下的alpha参数传输
  - 修复了多个类型错误（f_current是G1不是G2，acc_pk是元组等）

- **distributed/config.py**: 配置管理
  - 支持环境变量配置
  - 默认端口: DO=5001, SS=5002, Verifier=5003
  - **添加DEV_MODE开关**：允许共享alpha参数（仅用于开发测试）

- **distributed/client.py**: HTTP客户端库
  - DOClient: 调用DO服务器API
  - SSClient: 调用SS服务器API
  - VerifierClient: 调用Verifier服务器API

#### 2. HTTP服务器开发 ✅
- **distributed/do_server.py**: Data Owner服务器
  - `/init`: 初始化DO，生成CRS和密钥
  - `/create_batch`: 创建新批次
  - `/revoke_batch`: 撤销批次
  - `/update_batch`: 更新批次
  - `/get_crs`, `/get_global_pk`: 查询接口

- **distributed/ss_server.py**: Storage Server服务器
  - `/init`: 初始化SS
  - `/store_batch`: 存储批次数据
  - `/generate_dc_proof`: 生成DC查询证明
  - `/generate_da_proof`: 生成DA审计证明
  - `/add_server_key`, `/add_revoked_item`, `/update_batch`: 累加器更新

- **distributed/verifier_server.py**: Verifier服务器
  - `/init`: 初始化Verifier
  - `/verify_dc_query`: 验证DC查询证明
  - `/verify_da_audit`: 验证DA审计证明
  - `/update_global_pk`: 更新全局公钥

#### 3. 启动脚本 ✅
- **scripts/start_local.sh**: 启动3个服务器进程
- **scripts/stop_local.sh**: 停止所有服务器

#### 4. 测试 ✅
- **distributed_tests/test_distributed_e2e.py**: 端到端测试
  - 测试DC查询（单列）
  - 测试DC查询（多列）
  - 测试DA审计
  - 测试批次撤销

- **debug_dc_proof.py**: 调试脚本
  - 验证DC证明生成流程正确

## 遇到并解决的问题

### 1. 类型错误
- **问题**: `acc_pk`被当作字典，实际是元组
- **解决**: 修改序列化函数，将元组(g, g_hat, g_hat_s)序列化为列表

### 2. G1/G2混淆
- **问题**: `f_current`被序列化为G2，实际是G1
- **解决**: 修改serialization.py中serialize_global_pk使用serialize_g1

### 3. Secrets结构不匹配
- **问题**: SS期望键名是`m_matrix`和`t`，但序列化使用了`data_vectors`和`time_vector`
- **解决**: 统一使用`m_matrix`, `t`, `gamma_data_list`, `gamma_time`作为键名

### 4. ZR元素不能JSON序列化
- **问题**: m_matrix和t包含ZR元素，无法直接jsonify
- **解决**: 序列化时将ZR转为int，反序列化时再转回ZR

### 5. Python版本问题
- **问题**: 启动脚本使用python3，但用户环境是pyenv管理的python
- **解决**: 修改脚本使用`python`而不是`python3`

### 6. 跨进程验证失败（核心问题）
- **问题**: 单进程测试通过，但多进程HTTP测试验证失败
- **根本原因**: Charm库的单位元（identity element）序列化后，在另一个PairingGroup实例中反序列化时不再是单位元
- **影响**: 空累加器的非成员证明中w分量为单位元，跨进程传输后验证失败
- **解决**: 在serialize_g1/serialize_g2中特殊处理单位元，使用标记`__IDENTITY_G1__`/`__IDENTITY_G2__`代替序列化

## 当前状态

### ✅ 所有功能已验证通过
1. DO初始化和CRS生成
2. 批次创建和存储
3. DC查询证明生成和验证（单列和多列）
4. DA审计证明生成和验证
5. 批次撤销和非成员验证
6. **跨进程序列化/反序列化**
7. **所有4个E2E测试通过**

## 单进程 vs 多进程的关键差异

### 单进程实现
- 所有组件（DO/SS/Verifier）共享同一个PairingGroup实例
- 密码学元素在内存中直接传递，保持group上下文
- 单位元、配对运算等操作在同一group内完成
- **优点**: 简单，无需序列化
- **缺点**: 无法分布式部署

### 多进程实现
- 每个进程有独立的PairingGroup实例（虽然参数相同MNT224）
- 密码学元素通过序列化/反序列化跨进程传输
- 需要特殊处理：
  1. **单位元**：不能直接序列化，需要使用特殊标记
  2. **CRS一致性**（DEV_MODE）：共享alpha参数确保所有进程使用相同的CRS
  3. **数值类型**：ZR元素需要转换为int进行JSON传输
- **优点**: 支持分布式部署
- **缺点**: 需要处理序列化细节

### 解决方案总结

**问题1：单位元序列化**
- 单位元`O`直接序列化后，在新group中反序列化不再是单位元
- 解决：检测单位元并用字符串标记`"__IDENTITY_G1__"`替代

**问题2：CRS一致性（可选，仅DEV_MODE）**
- 虽然不是必需的，但为了调试方便，在DEV_MODE下共享alpha
- SS和Verifier用alpha重新生成CRS，确保与DO的CRS数学上完全一致
- 生产环境应禁用DEV_MODE

## 遇到并解决的问题
**根本原因**：
每个服务器进程独立创建`PairingGroup('MNT224')`实例时，虽然使用相同的曲线参数，但内部随机数生成器状态不同，导致：
1. 反序列化后的群元素在不同PairingGroup实例间存在微妙的不兼容
2. 累加器非成员证明使用的群运算结果不一致
3. 验证器无法正确验证跨进程生成的证明

**测试验证**：
```python
# 同一个group实例：验证通过
group = PairingGroup('MNT224')
# 序列化 + 反序列化
# 验证结果：True ✓

# 不同group实例：验证失败
group1 = PairingGroup('MNT224')  # DO使用
group2 = PairingGroup('MNT224')  # SS使用
group3 = PairingGroup('MNT224')  # Verifier使用
# 跨group序列化传输
# 验证结果：False ✗ ("批次已被撤销")
```

**影响范围**：
- DC查询验证失败
- DA审计验证失败
- 多列查询验证失败
- 仅批次撤销测试通过（因为逻辑简单，不涉及复杂的群运算）

### 🔄 待解决问题
1. **跨进程PairingGroup兼容性** - 需要共享CRS生成参数或使用固定种子

## 解决方案（已实施）

### ✅ 方案：修复单位元序列化
**核心发现**：
- 问题不在CRS不一致，而在于**Charm库的单位元序列化有bug**
- 单位元`O`序列化后，在新PairingGroup中反序列化不再是单位元
- 空累加器的非成员证明w分量为单位元，导致跨进程验证失败

**实现细节**：
```python
# distributed/serialization.py

def serialize_g1(elem: G1, group: PairingGroup) -> str:
    """序列化G1元素，特殊处理单位元"""
    if elem == group.init(G1, 1):
        return "__IDENTITY_G1__"  # 单位元用特殊标记
    return base64.b64encode(objectToBytes(elem, group)).decode('utf-8')

def deserialize_g1(data: str, group: PairingGroup) -> G1:
    """反序列化G1元素，特殊处理单位元"""
    if data == "__IDENTITY_G1__":
        return group.init(G1, 1)  # 在新group中重新创建单位元
    return bytesToObject(base64.b64decode(data), group)
```

**测试结果**：
```bash
# 修复前
跨group验证: False ❌

# 修复后
跨group验证: True ✅
所有E2E测试: PASSED (4/4) ✅
```

### 辅助方案：DEV_MODE共享alpha（可选）
虽然不是必需的，但保留了DEV_MODE功能用于调试：
- 当`DEV_MODE=true`时，DO发送alpha参数
- SS和Verifier用alpha重新生成CRS，确保完全一致
- 便于调试和比较中间结果
- **生产环境必须禁用**（`DEV_MODE=false`）

## 下一步建议

### Phase 1已完成 ✅
所有本地多进程+HTTP功能已实现并测试通过：
- ✅ DC查询（单列、多列）
- ✅ DA审计
- ✅ 批次撤销
- ✅ 跨进程序列化/反序列化

### Phase 2: Docker配置
1. 创建Dockerfile for each component (DO/SS/Verifier)
2. Docker Compose configuration
3. Network isolation and service discovery
4. Volume mounts for persistent storage
5. Environment variable configuration
6. Testing in Docker environment

### Phase 3: 多机部署
1. Kubernetes/云部署配置
2. 负载均衡和高可用
3. 安全通信（TLS/mTLS）
4. 监控和日志收集
5. 性能优化和压力测试

## 测试命令

### 启动服务器
```bash
bash scripts/start_local.sh
```

### 运行测试
```bash
# 运行所有E2E测试
python -m pytest distributed_tests/test_distributed_e2e.py -v

# 运行单个测试
python -m pytest distributed_tests/test_distributed_e2e.py::TestDistributedE2E::test_dc_query_single_column -v -s
```

### 停止服务器
```bash
bash scripts/stop_local.sh
```

### 查看日志
```bash
tail -f logs/*.log
```

## 环境配置

### DEV_MODE
- **默认值**: `true`
- **用途**: 开发模式，允许共享alpha参数
- **设置**: 通过环境变量`export DEV_MODE=false`禁用
- **生产环境**: 必须设置为`false`

## 技术总结

### 成功经验
1. **单位元序列化修复**：通过特殊标记避免Charm库的序列化bug
2. **分步骤调试**：创建多个调试脚本逐步定位问题
3. **跨进程测试**：对比单进程和多进程行为找出差异
4. **类型系统梳理**：明确每个数据结构的类型和序列化方式

### 技术难点
1. Charm库的序列化机制不透明，需要通过测试验证
2. PairingGroup实例的独立性导致跨进程兼容性问题
3. 密码学协议与分布式系统的结合需要仔细设计

### 代码质量
- ✅ 所有服务器使用Flask实现，代码结构清晰
- ✅ 客户端封装良好，API易于使用
- ✅ 测试覆盖完整，包含4个E2E测试用例
- ✅ 使用中文注释，逻辑说明简洁明了
- ✅ 错误处理和日志记录完善

---

**Phase 1状态：✅ 完成**
- 日期：2025-11-13
- 所有功能测试通过
- 文档已更新

## 文件清单

```
distributed/
├── __init__.py
├── config.py           # 配置
├── serialization.py    # 序列化工具
├── do_server.py        # DO服务器
├── ss_server.py        # SS服务器
├── verifier_server.py  # Verifier服务器
└── client.py           # 客户端库

distributed_tests/
├── __init__.py
└── test_distributed_e2e.py  # 端到端测试

scripts/
├── start_local.sh      # 启动脚本
└── stop_local.sh       # 停止脚本

debug_dc_proof.py       # 调试脚本
```

## 注意事项

1. 当前使用Flask开发服务器，生产环境需要使用WSGI服务器（如gunicorn）
2. 没有实现持久化存储，重启服务器会丢失所有数据
3. 没有实现错误重试和容错机制
4. 没有实现请求认证和授权
