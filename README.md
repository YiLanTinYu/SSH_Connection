# 交换机 SSH 自动化运维工具

> 面向企业网络工程师的多品牌交换机批量运维平台，支持图形化操作、多线程并发连接、自动品牌识别与配置保存。

---

## 目录

- [项目简介](#项目简介)
- [主要功能](#主要功能)
- [安装说明](#安装说明)
- [使用方法](#使用方法)
- [配置选项](#配置选项)
- [常见问题](#常见问题)
- [项目结构](#项目结构)
- [版本日志](#版本日志)
- [贡献指南](#贡献指南)

---

## 项目简介

**交换机 SSH 自动化运维工具（AOMT）** 是一款基于 Python + PyQt5 开发的图形化网络设备批量管理工具。将厂商差异封装在数据驱动的命令字典中，用户无需关心各品牌 CLI 语法差异，即可对大量交换机进行统一的批量操作。

**适用场景：**
- 网络设备日常巡检（版本、接口、VLAN、CPU、内存）
- 批量下发配置变更命令
- 快速定位二层网络上联口
- 批量保存设备配置

**技术栈：** Python 3.7+ · paramiko · PyQt5 · pandas · openpyxl · ThreadPoolExecutor · Nuitka

---

## 主要功能

### 多品牌自动识别

支持 5 大主流厂商，连接后通过两步识别树精准判断设备品牌和型号：

| 品牌 | 识别关键字 | 典型设备 |
|------|-----------|---------|
| H3C | `h3c`, `comware` | S5560, S5120, S6800 系列 |
| 华为 | `huawei`, `vrp` | S5735, S6730, CE 系列 |
| 锐捷 | `ruijie`, `rg-os` | RG-S5760, RG-NBS 系列 |
| 思科 | `cisco`, `ios`, `nx-os` | Catalyst, Nexus 系列 |
| TP-Link | `tp-link`, `jetstream`, `t2600` | T2600G, TL-SG 系列 |

### 批量操作

- **Excel 批量导入**：下载模板 → 填写 → 一键导入
- **设备去重**：按 IP + 端口自动跳过重复设备，避免重复连接
- **多线程并发**：`ThreadPoolExecutor` 调度，最多同时连接 5 台设备，任意设备完成即刻释放线程槽
- **列表管理**：支持移除选中设备或清空全部列表，危险操作均有二次确认

### 品牌感知命令翻译

命令文件只需按 H3C/Huawei 风格编写，工具在连接后自动转换为目标品牌的等价命令：

```
display interface brief   →  H3C/Huawei 原样执行
                          →  Cisco/锐捷 自动转为 show ip interface brief
display vlan              →  Cisco 自动转为 show vlan brief
display arp               →  Cisco 自动转为 show arp
```

### 保存配置

勾选"执行后保存配置"后，自动发送对应品牌的保存命令：

| 品牌 | 保存命令 |
|------|---------|
| H3C | `save force` |
| 华为 | `return` → `save` → `y` |
| 锐捷 / TP-Link | `write` |
| 思科 | `end` → `copy run start` |

### 二层上联口探测

一键定位交换机上联口，三步链式查询：

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
- 左侧操作区提供 **查看日志** 与 **清空日志**，清空日志只清空界面显示，不删除日志文件

### 常用运维工具

- **批量 Ping**：直接读取当前设备列表中的 IP，不需要再次选择 Excel
- 自动去重后逐个 Ping，中文结果实时显示在连接日志区域
- 任务完成后生成 `logs/pingYYYYMMDDHHMM.log` 文件

### 常用配置模板

- 支持一次添加多个配置模板文件（`.txt` / `.cfg` / `.conf` / `.log` / `.md` 等）
- 模板列表支持双击查看，方便忘记命令时快速查阅
- 移除模板只会从工具列表移除，不删除原始文件
- 本地模板列表保存在 `config/operation_templates.json`，该文件不会提交到 Git

---

## 安装说明

### 环境要求

| 要求 | 说明 |
|------|------|
| Python | 3.7 及以上 |
| 操作系统 | Windows · macOS · Linux |
| 网络 | SSH（TCP 22）可达目标设备 |

### 安装步骤

```bash
# 1. 克隆或下载项目
git clone https://github.com/YiLanTinYu/SSH_Connection.git
cd SSH_Connection

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动程序
python main.py
```

### 打包为独立可执行文件（可选）

```bash
# Windows（推荐，自动完成依赖安装、图标生成和 Nuitka 打包）
build.bat

# 手动打包
python -m pip install -r requirements.txt
python -m nuitka --standalone --onefile --assume-yes-for-downloads --mingw64 --enable-plugins=pyqt5 ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=app.ico ^
  --include-data-files=SSH_command.txt=SSH_command.txt ^
  --include-data-files=device_template.xlsx=device_template.xlsx ^
  --output-dir=dist ^
  --output-filename=H3C_SSH_Tool.exe ^
  main.py
# 生成文件位于 dist/ 目录
```

---

## 使用方法

### 界面概览

左侧为操作面板，包含：

- 添加设备：名称、品牌、IP 地址、端口、用户名、密码
- 批量导入：导入 Excel 文件、下载 Excel 模板
- 业务命令文件：选择文件、恢复默认
- 操作：执行后保存配置、探测二层上联口、开始连接、移除选中、清空列表、查看日志、清空日志
- 常用运维工具：批量 Ping
- 常用配置模板：添加模板、移除选中、双击查看

右侧为工作区，包含：

- 设备列表：设备名称、品牌、型号、IP 地址、IP 版本、端口、用户名、状态
- 连接日志：实时显示连接、命令执行、批量 Ping 等中文日志

程序默认窗口大小为 `2560 x 1600`，左侧区域可滚动，左右区域可拖动调整宽度；左侧最大宽度限制为窗口宽度的 50%。

### 手动添加设备

1. 在左侧面板选择品牌、输入 IP 地址（支持 IPv4 和 IPv6）
2. 填写 SSH 端口（默认 22）、用户名、密码
3. 可选填写设备名称，名称输入框默认提示为 `例如：SW1`
4. 点击 **"＋ 添加设备"** 按钮
5. 若设备 IP + 端口已存在，会自动跳过并提示

### Excel 批量导入

1. 点击 **"下载 Excel 模板"** 获取 `device_template.xlsx`
2. 按以下格式填写设备信息并保存：

   | 列名 | 必填 | 说明 | 示例 |
   |------|------|------|------|
   | `ip` | ✅ | IPv4 或 IPv6 地址 | `192.168.1.1` |
   | `username` | ✅ | SSH 登录用户名 | `admin` |
   | `password` | ✅ | SSH 登录密码 | `Admin@123` |
   | `brand` | 可选 | 品牌标识 | `h3c` / `huawei` / `cisco` |
   | `port` | 可选 | SSH 端口，默认 22 | `22` |
   | `name` | 可选 | 设备名称 | `核心交换机` |

3. 点击 **"导入 Excel 文件"** 选择填好的文件，设备自动加载到列表
4. 导入时会自动跳过重复设备，并在结果弹窗中显示新增、重复跳过和失败数量

### 管理命令文件

编辑项目根目录下的 `SSH_command.txt`，每行一条命令，`#` 开头为注释：

```bash
# 按 H3C/Huawei 风格编写，工具连接其他品牌时自动翻译
display version
display interface brief
display vlan
display cpu-usage
display memory
display arp
display ip routing-table
```

### 执行连接

1. 确认设备列表信息正确
2. 按需勾选运维选项：
   - **执行后保存配置**：所有命令执行完毕后自动保存设备配置
   - **探测二层上联口**：SSH 连接建立后执行三步链式上联口查询
3. 点击 **"▶ 开始连接"** 按钮
4. 在右下日志区域查看实时进度，设备列表"状态"列同步更新
5. 连接完成后点击 **"查看日志"** 查看日志文件位置，点击 **"清空日志"** 只清空界面日志显示

### 批量 Ping

1. 先通过手动添加或 **"导入 Excel 文件"** 将设备加入列表
2. 点击 **"批量 Ping"**
3. 工具会读取当前设备列表中的 IP，自动去重后逐个 Ping
4. 中文 Ping 结果会显示在右侧连接日志区域
5. 任务完成后自动生成 `logs/pingYYYYMMDDHHMM.log`

### 常用配置模板

1. 点击 **"添加模板"**，可一次选择多个模板文件
2. 添加后的模板会显示在左侧模板列表中
3. 双击模板可打开只读查看窗口
4. 点击 **"移除选中"** 只会从列表移除模板记录，不会删除原始文件

---

## 配置选项

### 命令字典扩展（`config/device_commands.py`）

**添加新品牌支持：**

```python
# 1. 在 BRAND_KEYWORDS 中添加识别关键字
BRAND_KEYWORDS = {
    'newbrand': ['newbrand', 'nb-os'],
}

# 2. 在 DEVICE_COMMANDS 中添加命令映射
DEVICE_COMMANDS = {
    'newbrand': {
        'nomore':            'terminal length 0',
        'save_config':       'write',
        'logout':            'exit',
        'l2_gw_ip_cmd':      'show ip route 0.0.0.0',
        'l2_gw_mac_cmd':     'show arp _GW_IP_',
        'l2_uplink_cmd':     'show mac-address-table address _GW_MAC_',
        'l2_uplink_mac_col': 1,
    },
}

# 3. 在 DEFAULT_COMMANDS 中添加默认命令
DEFAULT_COMMANDS = {
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

### 日志目录（`utils/logger.py`）

| 目录 | 说明 |
|------|------|
| `logs/success/` | SSH 连接成功记录 |
| `logs/failure/` | SSH 连接失败记录 |
| `logs/pingYYYYMMDDHHMM.log` | 批量 Ping 任务结果 |

SSH 日志文件命名格式：`类型_YYYYMMDD_HHMMSS.log`，按时间自动创建。
批量 Ping 日志文件命名格式：`pingYYYYMMDDHHMM.log`。

---

## 常见问题

### Q1：连接超时（`timed out`）

**原因：** 网络不通或 SSH 服务未开启。

```bash
# 检查网络连通性
ping 192.168.1.1

# 检查 SSH 端口（Windows PowerShell）
Test-NetConnection 192.168.1.1 -Port 22

# Linux / macOS
nc -zv 192.168.1.1 22
```

**解决方法：**
1. 确认防火墙放行 TCP 22 端口
2. 在交换机上启用 SSH：`ssh server enable`（H3C/华为）或 `ip ssh version 2`（Cisco）
3. 若使用非标准端口，在添加设备时修改端口号

---

### Q2：认证失败（`Authentication failed`）

**原因：** 用户名或密码错误，或账号无 SSH 登录权限。

**解决方法：**
1. 确认用户名和密码无误（注意大小写）
2. 确认账号存在且权限足够：`display local-user`（H3C）/ `display aaa local-user`（华为）
3. 确认设备允许密码认证方式登录

---

### Q3：品牌识别错误或显示"未知"

**原因：** `display version` / `show version` 输出中不含已知关键字。

**解决方法：**
1. 添加设备时手动选择正确品牌（工具优先使用手动指定的品牌）
2. 在 `config/device_commands.py` 的 `BRAND_KEYWORDS` 中补充该设备的关键字

---

### Q4：命令输出不完整（`--More--` 截断）

**原因：** 设备分页功能未成功关闭。

**解决方法：**
1. 确认 `config/device_commands.py` 中对应品牌的 `nomore` 命令正确
2. 手动在设备上测试：`screen-length disable`（H3C）/ `terminal length 0`（Cisco/锐捷）

---

### Q5：保存配置后设备未实际保存

**原因：** 部分型号保存命令有额外确认提示。

**解决方法：** 在 `config/device_commands.py` 的 `save_config` 中加入回车应答，例如：

```python
'save_config': 'return\rsave\r\ny\r',   # 华为带确认
'save_config': 'end\rcopy run start\r\r', # 思科带确认
```

---

### Q6：二层上联口探测无结果

**原因：** 设备没有默认路由，或 MAC 地址表中网关 MAC 已老化。

**排查：** 手动登录设备依次执行探测步骤：
```
display ip routing-table 0.0.0.0 0
display arp <网关IP>
display mac-address <网关MAC>
```

---

## 项目结构

```
SSH_Connection/
├── config/
│   ├── device_commands.py    # 多品牌命令字典（数据驱动）
│   ├── device_config.py      # 设备信息模型与配置管理
│   └── operation_templates.json # 本地配置模板列表（运行时生成，Git 忽略）
├── core/
│   └── ssh_manager_simple.py # SSH 连接管理器（多线程/品牌识别/上联探测）
├── ui/
│   └── main_window.py        # PyQt5 主界面
├── utils/
│   ├── logger.py             # 日志记录工具
│   └── ipv6_utils.py         # IPv4/IPv6 地址工具
├── docs/                     # 补充文档
├── Kylin/                    # 麒麟系统 CLI 工具（命令行版本）
│   ├── cli.py
│   └── requirements_kylin.txt
├── logs/                     # 运行日志（自动生成）
│   ├── success/              # 连接成功日志
│   └── failure/              # 连接失败日志
├── dist/                     # 打包输出目录
├── main.py                   # 程序入口
├── SSH_command.txt           # 业务命令文件（用户自定义）
├── device_template.xlsx      # Excel 导入模板
├── telnetlib_compat.py       # Python 3.14+ telnetlib 兼容层
├── build.bat                 # Windows 一键打包脚本
└── requirements.txt          # Python 依赖（含 Nuitka 打包工具）
```

---

## 版本日志

### v2.1.0（2026-06-12）— GitHub 原始版本

#### 用户界面
- 默认窗口大小调整为 `2560 x 1600`
- 左侧表单标签按最长标签列统一对齐，左右区域支持拖动调整
- 左侧区域改为滚动面板，窗口高度不足时不压缩添加设备表单
- 操作按钮文案统一为 **"移除选中"**
- **清空日志** 移至左侧操作区，与 **查看日志** 并排显示

#### 设备与日志
- Excel 导入按 IP + 端口自动去重，重复设备会跳过
- 移除设备、移除配置模板、清空设备列表均增加二次确认
- 连接日志默认字体提升到 16pt，日志和弹窗数据改为中文显示

#### 常用工具
- 新增 **常用运维工具** 区块
- 新增 **批量 Ping**，直接读取当前设备列表 IP，不再单独导入 Excel
- 批量 Ping 完成后生成 `logs/pingYYYYMMDDHHMM.log`

#### 配置模板
- 新增 **常用配置模板** 区块
- 支持多文件批量添加模板
- 模板支持双击只读查看
- 移除模板仅移除列表记录，不删除源文件

#### 打包与仓库
- Windows 打包方式切换为 Nuitka
- 本地模板列表 `config/operation_templates.json` 加入 Git 忽略
- 当前仓库地址更新为 `https://github.com/YiLanTinYu/SSH_Connection`

---

### v2.0.0（2026-03-18）— 重大优化版本

#### 核心引擎（`core/ssh_manager_simple.py`）
- **提示符正则升级**：宽容正则兼容所有主流厂商非标格式，消除提示符超时问题
- **品牌识别升级**：两步识别树（`display version` → `show version`），精准识别并提取设备型号
- **线程调度优化**：`ThreadPoolExecutor + as_completed`，任意设备完成即刻释放线程槽
- **保存配置**：新增 `save_after_exec` 开关，从命令字典动态获取各品牌保存命令
- **二层上联口探测**：完整三步链式查询（路由表 → ARP → MAC 表）

#### 命令配置（`config/device_commands.py`）
- 数据驱动重构：各品牌命令集中到单一字典，新增品牌只需添加一个 `dict` 条目
- 新增 `nomore` / `save_config` / `logout` / `l2_uplink_*` 命令集
- 新增 `translate_command_for_brand()` 函数，运行时自动翻译品牌命令

#### 用户界面（`ui/main_window.py`）
- 新增"执行后保存配置"、"探测二层上联口"勾选框
- 新增"移除选中"按钮，支持精细设备列表管理
- 设备列表新增"型号"列，连接后自动填充识别结果
- 日志每条增加 `[HH:MM:SS]` 时间戳

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
3. **传输加密**：使用标准 SSH 协议（SSH2），所有通信加密传输
4. **权限建议**：建议为运维账号配置最小必要权限，避免使用管理员账号

---

## 贡献指南

欢迎通过 Issue 或 Pull Request 参与改进本项目。

### 提交 Issue

- 描述复现步骤和期望行为
- 附上相关日志（`logs/` 目录下的对应文件）
- 注明设备品牌、型号和固件版本

### 提交 Pull Request

```bash
# 1. Fork 本仓库并创建功能分支
git checkout -b feature/add-juniper-support

# 2. 完成开发后提交
git commit -m "feat: add Juniper device support"

# 3. 发起 Pull Request
```

**代码规范：**
- 遵循 PEP 8，注释使用中文
- 新增品牌需同时补充：`BRAND_KEYWORDS`、`DEVICE_COMMANDS`（含 `nomore`、`save_config`、`l2_uplink_*`）、`DEFAULT_COMMANDS`
- 新增配置项需在 README 的"配置选项"章节同步说明
- 禁止在代码中硬编码密码或 IP 地址

---

## 许可证

本项目采用 MIT 许可证。

---

**交换机 SSH 自动化运维工具 v2.1.0** | 最后更新：2026-06-12
