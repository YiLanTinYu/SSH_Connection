# 交换机 SSH 自动化运维工具

> 面向企业网络工程师的多品牌交换机批量运维平台，支持图形化操作、多线程并发连接、自动品牌识别与配置保存。

---

## 目录

- [项目简介](#项目简介)
- [主要功能](#主要功能)
- [安装步骤](#安装步骤)
- [使用说明](#使用说明)
- [配置选项](#配置选项)
- [常见问题解答](#常见问题解答)
- [版本更新日志](#版本更新日志)
- [贡献指南](#贡献指南)

---

## 项目简介

**交换机 SSH 自动化运维工具**是一款基于 Python + PyQt5 开发的图形化网络设备批量管理工具。它借鉴了 [w-sw-ssh](../w-sw-ssh-master) 的优秀设计理念，将厂商差异封装在数据驱动的命令字典中，用户无需关心各品牌 CLI 语法差异，即可对大量交换机进行统一的批量操作。

**适用场景：**
- 网络设备日常巡检（版本、接口、VLAN、CPU、内存）
- 批量下发配置变更命令
- 快速定位二层网络上联口
- 批量保存设备配置

**技术栈：** Python 3.7+ · paramiko · PyQt5 · pandas · openpyxl · ThreadPoolExecutor

---

## 主要功能

### 多品牌自动识别

支持 5 大主流厂商，通过两步识别树精准判断设备品牌和型号：

| 品牌 | 识别关键字 | 典型设备 |
|------|-----------|---------|
| H3C | `h3c`, `comware` | S5560, S5120, S6800 系列 |
| 华为 | `huawei`, `vrp` | S5735, S6730, CE 系列 |
| 锐捷 | `ruijie`, `rg-os` | RG-S5760, RG-NBS 系列 |
| 思科 | `cisco`, `ios`, `nx-os` | Catalyst, Nexus 系列 |
| TP-Link | `tp-link`, `jetstream`, `t2600` | T2600G, TL-SG 系列 |

### 批量操作

- **Excel 批量导入**：下载模板 → 填写 → 一键导入
- **多线程并发**：`ThreadPoolExecutor` 调度，最多同时连接 5 台设备，任意设备完成即刻释放线程槽
- **单独删除**：支持在设备列表中选中并删除单台设备，无需全部清空

### 品牌感知命令翻译

借鉴 w-sw-ssh `cmd_prefix` 机制实现 GUI 版运行时翻译，命令文件只需按 H3C/Huawei 风格编写，工具在连接后自动转换为目标品牌的等价命令：

```
# SSH_command.txt（只需维护一份）
display interface brief   →  H3C/Huawei 原样执行
                          →  Cisco/锐捷 自动转为 show ip interface brief
display vlan              →  Cisco 自动转为 show vlan brief
display arp               →  Cisco 自动转为 show arp
```

### 保存配置

勾选"执行后保存配置"后，工具在命令执行完毕后自动发送对应品牌的保存命令：

| 品牌 | 保存命令 |
|------|---------|
| H3C | `save force` |
| 华为 | `return` → `save` → `y` |
| 锐捷 / TP-Link | `write` |
| 思科 | `end` → `copy run start` |

### 二层上联口探测

借鉴 w-sw-ssh `uf_get_l2_uplink` 三步链式查询，一键定位交换机上联口：

```
步骤 1：查路由表获取默认网关 IP
        display ip routing-table 0.0.0.0 0

步骤 2：查 ARP 表获取网关 MAC 地址
        display arp <网关IP>

步骤 3：查 MAC 地址表定位上联接口
        display mac-address <网关MAC>
```

### 日志管理

- 每条日志带 `[HH:MM:SS]` 时间戳
- 成功 / 失败日志自动着色区分
- 日志文件按类型分目录保存：`logs/success/` · `logs/failure/`

---

## 安装步骤

### 1. 环境要求

| 要求 | 说明 |
|------|------|
| Python | 3.7 及以上 |
| 操作系统 | Windows · macOS · Linux |
| 网络 | SSH（TCP 22）可达目标设备 |

### 2. 克隆或下载项目

```bash
git clone <仓库地址>
cd Switch_SSH_Tools
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 内容：

```
paramiko==3.5.0
PyQt5==5.15.11
pandas==2.2.3
openpyxl==3.1.5
cryptography==44.0.0
netmiko==4.3.0
```

### 4. 启动程序

```bash
python main.py
```

### 5. 打包为独立可执行文件（可选）

```bash
# Windows（已提供 build.bat）
build.bat

# 手动使用 PyInstaller
pyinstaller build.spec
# 生成文件位于 dist/ 目录
```

---

## 使用说明

### 界面概览

```
┌─────────────────────────────────────────────────────┐
│  添加设备面板 (左)       │  设备列表 (右上)          │
│  - 品牌选择              │  名称/品牌/型号/IP/状态   │
│  - IP / 端口 / 账密      ├───────────────────────────┤
│  - 手动添加 / 批量导入   │  操作面板 (右中)           │
│                          │  - 保存配置 勾选框        │
│                          │  - 二层上联口探测 勾选框  │
│                          │  - 开始连接 / 删除选中    │
│                          │  - 查看日志               │
│                          ├───────────────────────────┤
│                          │  实时日志 (右下)           │
└─────────────────────────────────────────────────────┘
```

### 手动添加设备

1. 在左侧"添加设备"面板选择设备品牌
2. 输入 IP 地址（支持 IPv4 和 IPv6）
3. 输入 SSH 端口（默认 22）
4. 填写用户名和密码
5. 可选填写设备名称（留空则默认为 `品牌_IP`）
6. 点击 **"添加设备"** 按钮

### 批量导入设备

1. 点击 **"下载 Excel 模板"** 获取 `device_template.xlsx`
2. 按以下格式填写设备信息：

   | 列名 | 说明 | 示例 |
   |------|------|------|
   | `name` | 设备名称（可选） | 核心交换机 |
   | `brand` | 品牌标识 | `h3c` / `huawei` / `ruijie` / `cisco` / `tplink` |
   | `ip` | IP 地址 | `192.168.1.1` 或 `2001:db8::1` |
   | `port` | SSH 端口 | `22` |
   | `username` | 登录用户名 | `admin` |
   | `password` | 登录密码 | `Admin@123` |

3. 点击 **"导入 Excel 文件"** 选择填好的文件，设备自动加载到列表

### 管理命令文件

编辑项目根目录下的 `SSH_command.txt`，每行一条命令，`#` 开头为注释：

```bash
# SSH_command.txt 示例
display version
display interface brief
display vlan
display cpu-usage
display memory
```

> **提示：** 按 H3C/Huawei 风格编写即可，工具连接 Cisco/锐捷设备时会自动翻译命令。

### 执行连接

1. 确认设备列表信息正确
2. 按需勾选运维选项：
   - **执行后保存配置**：命令执行完毕后自动保存设备配置
   - **探测二层上联口**：通过三步链式查询定位上联端口
3. 点击 **"▶ 开始连接"** 按钮
4. 在右下日志区域查看实时进度，设备列表"状态"列同步更新
5. 连接完成后可点击 **"📋 查看日志"** 查看详细报告

### 删除设备

- **删除选中**：在设备列表中单击选择目标行，点击 **"✂ 删除选中"** 删除该设备
- **清空列表**：点击 **"🗑 清空列表"** 删除所有设备

---

## 配置选项

### 命令字典扩展（`config/device_commands.py`）

#### 为现有品牌添加新命令

```python
# 在对应品牌的字典中新增条目
DEVICE_COMMANDS = {
    'h3c': {
        ...
        'display_stp': 'display stp brief',   # 新增 STP 状态命令
    },
    ...
}
```

#### 添加新品牌支持

```python
# 1. 在 BRAND_KEYWORDS 中添加识别关键字
BRAND_KEYWORDS = {
    ...
    'newbrand': ['newbrand', 'nb-os'],
}

# 2. 在 DEVICE_COMMANDS 中添加命令映射
DEVICE_COMMANDS = {
    ...
    'newbrand': {
        'display_version':   'show version',
        'nomore':            'terminal length 0',
        'save_config':       'write',
        'logout':            'exit',
        'l2_gw_ip_cmd':      'show ip route 0.0.0.0',
        'l2_gw_mac_cmd':     'show arp _GW_IP_',
        'l2_uplink_cmd':     'show mac-address-table address _GW_MAC_',
        'l2_uplink_mac_col': 1,
        # ... 其他查询命令
    },
}

# 3. 在 DEFAULT_COMMANDS 中添加默认命令
DEFAULT_COMMANDS = {
    ...
    'newbrand': 'show version',
}
```

### SSH 连接参数（`core/ssh_manager_simple.py`）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_connections` | `5` | 最大并发连接数 |
| `CONNECT_TIMEOUT` | `30` 秒 | TCP 握手超时 |
| `RECV_TIMEOUT` | `10` 秒 | 单次命令接收超时 |
| `MAX_READ_BYTES` | `65535` | 单次最大读取字节数 |

修改方式：

```python
# 在 main_window.py 的 start_connection 中调整并发数
self.ssh_manager = SSHManager(max_connections=10)  # 改为 10 并发
```

### 日志配置（`utils/logger.py`）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 日志根目录 | `logs/` | 相对于项目根目录 |
| 成功日志 | `logs/success/` | SSH 连接成功记录 |
| 失败日志 | `logs/failure/` | SSH 连接失败记录 |
| 文件命名格式 | `类型_YYYYMMDD_HHMMSS.log` | 按时间自动创建 |

### 运维选项说明

| 选项 | 触发时机 | 对应 w-sw-ssh 参数 |
|------|---------|-------------------|
| 执行后保存配置 | 所有命令执行完毕后 | `--save` |
| 探测二层上联口 | SSH 连接建立后 | `--l2_sw` |

---

## 常见问题解答

### Q1：连接超时，提示 `timed out`

**原因：** 网络不通或 SSH 服务未开启。

**排查步骤：**
```bash
# 检查网络连通性
ping 192.168.1.1

# 检查 SSH 端口是否开放（Windows）
Test-NetConnection 192.168.1.1 -Port 22

# Linux / macOS
nc -zv 192.168.1.1 22
```

**解决方法：**
1. 确认防火墙放行 TCP 22 端口
2. 在交换机上执行 `ssh server enable`（H3C/华为）或 `ip ssh version 2`（Cisco）
3. 若使用非标准端口，在添加设备时修改端口号

---

### Q2：认证失败，提示 `Authentication failed`

**原因：** 用户名或密码错误，或设备不允许该账号 SSH 登录。

**解决方法：**
1. 确认用户名和密码无误（注意大小写）
2. 在交换机上确认账号存在且权限足够：
   ```
   # H3C
   display local-user
   # 华为
   display aaa local-user
   ```
3. 确认设备 SSH 配置允许密码认证而非仅密钥认证

---

### Q3：品牌识别错误或显示"未知"

**原因：** `display version` / `show version` 输出中不含已知关键字。

**解决方法：**
1. 在添加设备时手动选择正确品牌，工具会优先使用手动指定的品牌
2. 打开 `config/device_commands.py`，在 `BRAND_KEYWORDS` 中补充该设备的识别关键字：
   ```python
   'h3c': ['h3c', 'comware', '你的设备特有关键字'],
   ```

---

### Q4：命令执行完毕但型号列为空

**原因：** 设备版本输出格式特殊，正则未能匹配到型号字段。

**解决方法：** 在 `core/ssh_manager_simple.py` 的 `_extract_model()` 中补充该品牌的正则表达式：

```python
# 示例：补充 H3C 特殊型号格式
patterns = [
    r'H3C\s+(S\w+)',
    r'WS\d{4}[A-Z\-]*',   # 新增自定义格式
    r'Ruijie\s+(RG-\S+)',
]
```

---

### Q5：`display arp` 等命令被截断，输出不完整

**原因：** 设备默认开启分页（`--More--`），工具未成功关闭。

**解决方法：**
1. 确认 `config/device_commands.py` 中对应品牌的 `nomore` 命令正确
2. 手动在设备上测试 nomore 命令：
   ```
   # H3C
   screen-length disable
   # 华为
   screen-length 0 temp
   # Cisco / 锐捷
   terminal length 0
   ```

---

### Q6：保存配置后设备未实际保存

**原因：** 部分型号在执行保存命令时有额外确认提示。

**解决方法：** 在 `config/device_commands.py` 的 `save_config` 中加入回车应答：

```python
# 华为已内置 \ny\r 应答，如需修改：
'save_config': 'return\rsave\r\ny\r',

# 思科已内置确认，如设备还有其他提示可追加：
'save_config': 'end\rcopy run start\r\r',
```

---

### Q7：二层上联口探测无结果

**原因：** 设备没有默认路由，或 MAC 地址表中网关 MAC 已老化。

**排查步骤：**
1. 手动登录设备执行探测步骤：
   ```
   display ip routing-table 0.0.0.0 0
   display arp <网关IP>
   display mac-address <网关MAC>
   ```
2. 确认设备是纯二层交换机（有默认路由指向网关即可使用此功能）

---

## 项目结构

```
Switch_SSH_Tools/
├── config/
│   ├── device_commands.py    # 多品牌命令字典（数据驱动）
│   └── device_config.py      # 设备信息模型与管理
├── core/
│   └── ssh_manager_simple.py # SSH 连接管理器（多线程 / 品牌识别 / 上联探测）
├── ui/
│   └── main_window.py        # PyQt5 主界面
├── utils/
│   ├── logger.py             # 日志记录工具
│   └── ipv6_utils.py         # IPv4/IPv6 地址工具
├── docs/                     # 文档目录
├── logs/                     # 运行日志（自动生成）
│   ├── success/              # 成功连接日志
│   └── failure/              # 失败连接日志
├── SSH_command.txt           # 业务命令文件（用户自定义）
├── device_template.xlsx      # Excel 导入模板
├── main.py                   # 程序入口
├── requirements.txt          # Python 依赖
├── build.bat                 # Windows 打包脚本
└── build.spec                # PyInstaller 打包配置
```

---

## 版本更新日志

### v2.0.0（2026-03-18）— 重大优化版本

**借鉴 w-sw-ssh 优秀设计，进行以下系统性升级：**

#### 核心引擎（`core/ssh_manager_simple.py`）
- **提示符正则升级**：移植 w-sw-ssh 久经验证的宽容正则，兼容所有主流厂商非标格式，消除提示符超时问题
- **品牌识别升级**：从单步匹配升级为两步识别树（`display version` → `show version`），精准识别并提取设备型号
- **线程调度优化**：用 `ThreadPoolExecutor + as_completed` 替代固定工作线程，任意设备完成即刻释放线程槽，整体吞吐提升
- **保存配置功能**：新增 `save_after_exec` 开关，从命令字典动态获取各品牌保存命令，消除 if-else 分散
- **二层上联口探测**：完整移植 w-sw-ssh `uf_get_l2_uplink`，支持三步链式查询（路由表→ARP→MAC表）

#### 命令配置（`config/device_commands.py`）
- **数据驱动重构**：将各品牌命令集中到单一字典，新增品牌只需添加一个 `dict` 条目
- **新增运维命令**：为所有品牌补充 `nomore` / `save_config` / `logout` / `l2_uplink_*` 命令
- **品牌感知翻译**：新增 `translate_command_for_brand()` 函数，运行时自动将 H3C 命令翻译为目标品牌语法

#### 用户界面（`ui/main_window.py`）
- 新增 **"执行后保存配置"** 勾选框（对应 w-sw-ssh `--save`）
- 新增 **"探测二层上联口"** 勾选框（对应 w-sw-ssh `--l2_sw`）
- 新增 **"✂ 删除选中"** 按钮，支持精细设备列表管理
- 设备列表新增 **"型号"** 列，连接后自动填充识别结果
- 日志每条增加 `[HH:MM:SS]` 时间戳
- 连接成功后状态列显示品牌名，快速确认识别结果

---

### v1.0.0（2026-03-12）— 初始发布

- 基础 SSH 多线程连接框架
- 支持 H3C / 华为 / 锐捷 / 思科 四品牌
- Excel 批量导入功能
- PyQt5 图形化界面
- 日志分目录保存

---

## 安全说明

1. **密码安全**：密码仅在内存中使用，不写入任何文件或日志
2. **日志脱敏**：日志文件中不包含密码信息
3. **传输加密**：使用标准 SSH 协议（TLS/SSH2），所有通信加密传输
4. **权限建议**：建议为运维账号配置最小必要权限，避免使用管理员账号

---

## 贡献指南

欢迎通过 Issue 或 Pull Request 参与改进本项目。

### 提交 Issue

- 描述复现步骤和期望行为
- 附上相关日志（`logs/` 目录下的对应文件）
- 注明设备品牌、型号和系统版本

### 提交 Pull Request

1. Fork 本仓库并创建功能分支：
   ```bash
   git checkout -b feature/add-juniper-support
   ```
2. 遵循现有代码风格（PEP 8，中文注释）
3. 新增品牌支持时，至少补充以下内容：
   - `BRAND_KEYWORDS` 识别关键字
   - `DEVICE_COMMANDS` 完整命令字典（含 `nomore`、`save_config`、`logout`、`l2_uplink_*`）
   - `DEFAULT_COMMANDS` 默认版本命令
4. 提交时附上测试设备的品牌/型号信息

### 代码规范

- 函数和类使用 Google 风格 docstring
- 新增配置项需在 README 的"配置选项"章节同步说明
- 禁止在代码中硬编码密码或 IP 地址

---

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE)。

---

**交换机 SSH 自动化运维工具 v2.0.0** | 最后更新：2026-03-18
