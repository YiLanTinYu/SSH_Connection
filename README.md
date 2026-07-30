# AOMT - 交换机自动化运维工具

> 面向网络运维人员的 PyQt5 图形化工具，用于批量管理 H3C、Huawei、Ruijie、Cisco 和 TP-Link 交换机的 SSH 运维任务。

**当前版本：v1.0.0**

**作者：YiLanTinYu**

## 项目简介

AOMT（Automated Operations and Maintenance Tool）提供设备管理、Excel 批量导入、多品牌 SSH 连接、逐设备脚本、批量网络诊断、配置备份与对比、子网计算、运行日志和配置模板查阅等功能。

它适合以下场景：

- 批量执行交换机巡检命令
- 为不同交换机执行各自的命令脚本
- 检查多台设备的网络连通性
- 批量检查 TCP 端口、SSH 登录和网络路径
- 备份并比较交换机配置
- 计算 IPv4/IPv6 子网信息
- 查看交换机品牌、型号及执行状态
- 辅助探测二层上联端口
- 通过串口连接交换机 Console
- 从设备列表打开单台设备的 SSH 交互终端
- 集中保存和查阅常用配置模板

## 主要功能

### 设备管理

- 手动添加设备
- 从 Excel 批量导入设备
- 下载标准 Excel 模板
- 支持密码认证和 SSH 私钥认证
- 支持首次信任、严格校验和不校验三种 Host Key 策略
- 支持设备分组、标签、搜索和执行范围筛选
- 按 `IP + SSH 端口` 自动跳过重复设备
- 校验 IPv4、IPv6 和端口
- 支持移除选中设备和清空设备列表
- 删除、清空操作均有二次确认
- 设备状态在任务执行过程中实时更新
- 按设备保存完整命令输出、错误和耗时，可导出 Excel、CSV 或 JSON

### Excel 密码加密

程序支持将 Excel 中的设备密码和私钥口令转换为密文：

- 使用 AES-256-GCM 加密设备密码
- 使用 PBKDF2-SHA256 从主密码派生密钥
- 每个密码使用独立的随机盐和随机数
- 主密码不写入 Excel、日志或程序配置
- 加密文件可复制到其他电脑使用
- 导入加密 Excel 时自动要求输入主密码
- 主密码错误或密文损坏时拒绝解密
- 导入明文密码时显示安全警告

结果中心和运行日志不会保存设备密码或私钥口令。

加密后的单元格以以下标识开头：

```text
AOMT_ENC_V1$
```

主密码至少需要 8 个字符。主密码丢失后无法恢复设备密码，请妥善保管。

### 多品牌支持

| 品牌 | 典型系统 |
|------|----------|
| H3C | Comware |
| Huawei | VRP |
| Ruijie | RGOS |
| Cisco | IOS / NX-OS |
| TP-Link | JetStream 等系列 |

连接成功后，程序会尝试自动识别品牌和型号。无法识别时，使用设备信息中填写的品牌。品牌信息仅用于程序内部的分页、保存和上联探测等操作。

### 业务命令原样执行

程序不会自动翻译或改写用户业务脚本。命令文件中的有效命令会逐行原样发送，避免未经真实设备验证的跨品牌转换误导用户。请按目标设备的品牌、系统和版本编写脚本；存在差异时，可分别选择自定义文件，或使用“按设备匹配”模式。

### 两种脚本模式

#### 统一脚本

所有设备执行同一个命令文件。默认文件为：

```text
SSH_command.txt
```

也可以在界面中选择其他 TXT 文件。

#### 按设备匹配

每台设备执行与设备名称同名的 TXT 文件。程序只按设备名称匹配，不使用 IP、品牌或默认脚本回退。

示例：

```text
设备名称       脚本文件
SW_CORE_01  -> SW_CORE_01.txt
SW_ACCESS_2 -> SW_ACCESS_2.txt
```

使用方法：

1. 在“业务命令文件”中选择“按设备匹配”
2. 选择存放设备脚本的目录
3. 确保每台设备都有同名 TXT 文件
4. 点击“开始连接”
5. 在执行前的预览窗口核对“设备 -> 脚本”关系

匹配不区分文件名大小写。设备名称中不建议使用 Windows 文件名禁止字符：

```text
< > : " / \ | ? *
```

未找到同名脚本的设备会标记为未匹配并跳过命令执行。

### SSH 批量任务

- 使用线程池并发处理设备
- 默认最多同时连接 5 台设备
- 实时输出中文连接和命令日志
- 支持在运行中点击“停止连接”
- 停止后不再派发新任务，并关闭活动连接
- 可选“执行后保存配置”
- 可选“探测二层上联口”
- 完成后显示成功、失败和成功率

### 批量 Ping

批量 Ping 可组合使用当前设备列表、手工地址和 CIDR 网段，不需要重复选择 Excel。

- 自动去重
- 支持 IPv4 和 IPv6
- 支持输入 `192.168.10.0/24`、`2026:1000:120::/120` 等 CIDR 网段
- IPv4 网段自动排除网络地址和广播地址，合并后单次最多 4096 个目标
- 最多使用 32 路受控并发，缩短网段内大量地址的等待时间
- 中文显示成功、失败和统计结果
- 完成后自动生成日志文件

日志文件格式：

```text
logs/pingYYYYMMDDHHMM.log
```

如果同一分钟内存在同名日志，程序会自动增加序号。

### 常用运维工具

工具默认复用当前设备列表，无需重复导入：

- **批量 Ping**：按设备、手工地址或 CIDR 网段检查 IPv4/IPv6 可达性并生成 `ping*.log`
- **端口检测**：批量检测用户指定的 TCP 端口；默认 `22,23,80,443`，不做全端口扫描
- **SSH 登录测试**：只验证 SSH 网络连接和账号认证，不打开设备 Shell、不执行设备命令
- **路由跟踪**：调用 Windows `tracert` 或兼容系统的 `traceroute`，记录到设备的网络路径
- **配置对比**：比较两份本地配置文件，以统一差异格式显示新增和删除行，并可保存结果
- **配置备份**：按识别品牌执行只读查询命令，为每台设备保存版本化 `.cfg` 配置和 `.json` 元数据；空输出或无效命令不会生成文件
- **子网计算**：计算 IPv4/IPv6 网络地址、前缀、地址数量及 IPv4 可用范围
- **串口控制台**：连接 Windows COM 串口，进行交换机 Console 调试和开局操作
- **SSH 交互终端**：从当前设备列表选择单台设备，打开独立的交互式 SSH Shell
- **文件传输服务**：临时启动 FTP 或 TFTP 服务，在共享目录与交换机之间上传、下载配置和系统文件
- **网络抓包**：调用本机 Wireshark 的 Dumpcap 选择网卡并保存标准 `.pcapng` 文件，抓包完成后可直接用 Wireshark 打开
- **一键设备巡检**：以品牌明确的只读命令采集 H3C/Comware、Huawei VRP 的 CPU、内存、温度、风扇、电源、接口摘要和硬件信息；可勾选内置项目、按品牌增加自定义 `display` 查询命令，并保存为巡检方案
- **IP/MAC 终端定位**：按“IPv4 → ARP → MAC 地址表 → 交换机接口”流程在已选 H3C 或 Huawei 设备中定位终端
- **接口综合诊断**：检查 H3C、Huawei 接口物理/协议状态、速率、双工、链路类型、PVID及光模块诊断和告警输出

批量 Ping、端口检测、SSH 登录测试、路由跟踪和三个设备诊断工具共用目标选择窗口：

- 可勾选当前手工添加或 Excel 导入的设备，默认全选
- 可同时手动补充多个 IPv4、IPv6 或主机名
- 批量 Ping 还可补充一个或多个 CIDR 网段，并自动展开可 Ping 地址
- 手工目标支持换行、空格、英文/中文逗号和分号分隔
- 所有目标来源合并后自动去重
- SSH 手工目标支持 `主机名:端口` 和 `[IPv6]:端口`，并单独填写共用用户名和密码
- Excel/设备列表中的 SSH 目标继续使用各自保存的认证参数

端口检测、SSH 登录测试、路由跟踪、配置备份和设备诊断均在后台线程执行，期间不会冻结主界面。诊断结果进入执行结果中心，可导出 Excel、CSV 或 JSON；批量任务结束后会在 `logs/` 下生成带时间戳的中文日志。

执行结果将耗时拆分为“总耗时、连接准备、任务执行”：连接准备包括 SSH 握手、认证、Shell 初始化和品牌识别，任务执行表示连接成功后的实际运维命令阶段。

三个设备诊断工具对 H3C/Comware 和 Huawei VRP 使用独立命令配置，不进行跨品牌自动翻译。检测到其他品牌时会停止诊断并明确提示，不会发送未经验证的命令。结构化解析使用 [NTC Templates](https://github.com/networktocode/ntc-templates)、[NAPALM H3C Comware](https://github.com/napalm-automation-community/napalm-h3c-cw7-ssh) 模板，并参考 [NAPALM Huawei VRP](https://github.com/napalm-automation-community/napalm-huawei-vrp) 的环境采集命令与解析方式，详情见 `THIRD_PARTY_NOTICES.md`。

巡检方案保存在 `%LOCALAPPDATA%\AOMT\health_check_profiles.json`。内置“标准巡检”不可覆盖或删除；自定义命令必须是单行 `display ...` 查询命令，只展示原始输出，不参与自动健康判定。

配置备份由用户选择根目录，程序按设备建立子目录：

```text
所选备份目录/
└── SW10/
    ├── SW10_20260729_103520.cfg
    └── SW10_20260729_103520.json
```

- `.cfg` 使用 UTF-8 纯文本，只保存清理后的设备配置正文
- 自动去除 ANSI 控制符、分页提示、查询命令回显和独立设备提示符
- `.json` 保存设备名称、IP、端口、识别品牌、查询命令、备份时间、行数和 SHA-256
- JSON 元数据不保存用户名、密码、私钥路径或私钥口令
- 每次备份保留一个时间版本；同秒重名时自动增加序号
- 配置对比继续支持 `.cfg`、`.conf`、`.txt` 和 `.log`

### 共享终端仿真

串口控制台和 SSH 交互终端共用基于 `pyte` 的 VT100/ANSI 终端控件，支持：

- 光标定位、回车覆盖、退格、清行和清屏
- ANSI 16 色、粗体、斜体、下划线和反色显示
- 方向键、Home、End、Delete、Tab、Esc、Ctrl 组合键
- UTF-8、GBK、GB18030 和 BIG5 编码
- 按窗口尺寸调整终端行列数
- 高频输出按短周期合并刷新，相同样式的连续字符批量绘制
- 点击终端空白区域后自动恢复设备端真实光标位置，拖动选择文本不受影响
- 窗口放大或缩小时保留当前屏幕、历史内容和有效光标位置
- 有选区时 `Ctrl+C` 复制，无选区时 `Ctrl+C` 向设备发送中断
- `Ctrl+V` / `Ctrl+Shift+V` 粘贴并发送，右键菜单同时提供复制、粘贴、全选和发送中断
- 会话日志保存

### 串口控制台

点击“常用运维工具 → 串口控制台”打开独立窗口。当前支持：

- 自动扫描和刷新 Windows COM 端口
- 波特率、数据位、校验位、停止位和流控
- UTF-8、GBK、GB18030 和 BIG5 编码
- 默认使用交换机 Console 常见的 CR 回车，也可选择 LF、CRLF 或不追加行结束符
- DTR 和 RTS 控制；Enter、Ctrl+C、Ctrl+Z、Esc 和 Tab 可直接通过键盘输入
- 点击深色终端区域可直接输入，支持方向键、退格、Delete、Home、End 和翻页键
- 深色终端与下方命令框按焦点切换，任意时刻只有一个输入区可写并显示输入光标
- 有选区时 `Ctrl+C` 或 `Ctrl+Shift+C` 复制；`Ctrl+V` 或 `Ctrl+Shift+V` 将剪贴板内容发送到串口
- 隐藏输入，适合输入 Console 登录密码
- 清屏以及保存 UTF-8 会话日志
- 保存、调用和删除常用串口连接配置
- 串口读取在后台线程运行，不阻塞主界面
- “串口已打开”只表示电脑成功打开 COM 端口，不能据此判断交换机是否通电
- 正常连接时每 2 秒检查一次端口、句柄和可用线路信号；适配器拔出后停止会话，并每 1 秒检查是否恢复

串口连接配置保存在：

```text
%LOCALAPPDATA%\AOMT\serial_profiles.json
```

配置文件只保存串口参数，不保存 Console 用户名或密码。当前版本是交互式串口终端，不会自动向串口批量下发 SSH 业务脚本。

### SSH 交互终端

点击“常用运维工具 → SSH 交互终端”，设备框同时支持下拉选择和手动输入。存在手工添加或 Excel 导入的设备时，可展开列表选择并自动带出连接参数；也可直接覆盖输入 IPv4、IPv6 或主机名并填写端口、用户名和密码。选择已有设备时，终端复用设备中的认证信息和 Host Key 策略，不单独保存一份凭据。

- 使用 Paramiko `invoke_shell()` 打开交互式 PTY
- 支持密码认证和私钥认证
- 支持 TOFU、严格校验和不校验三种 Host Key 策略
- 终端尺寸变化时同步调用远端 PTY 尺寸调整
- SSH 读取和发送在独立线程中运行
- 可清屏并将当前终端内容保存为 UTF-8 日志

SSH 交互终端不会自动执行品牌识别、禁分页或业务脚本；输入的内容会原样发送到当前设备。

### FTP/TFTP 文件传输

点击“常用运维工具 → 文件传输服务”打开独立窗口。当前支持：

- 在 TFTP 和 FTP 服务之间切换，选择监听网卡、端口和共享目录
- FTP 使用临时用户名和随机密码，支持配置被动端口范围
- 默认只允许交换机下载文件；勾选“允许交换机上传文件”后才开放写入
- 从窗口添加、刷新或移除共享文件
- 显示客户端连接、登录、上传、下载、中断和错误日志
- 服务运行在后台线程，关闭窗口时自动停止并释放端口
- 提供 H3C 下载和上传参考命令，但不会自动向交换机发送

TFTP 和 FTP 都是明文协议，只应在可信的隔离运维网络中临时启用。监听 `0.0.0.0` 表示接受所有 IPv4 网卡的连接；实际给交换机填写地址时，应使用与交换机运维网段互通的本机网卡 IP。Windows 防火墙可能在首次启动时请求网络访问权限。

### 网络抓包

点击“常用运维工具 → 网络抓包”打开独立窗口。该功能不会自行实现抓包驱动，而是调用本机 Wireshark 随附的 Dumpcap 和 TShark：

- 自动检测 Wireshark 安装位置并列出 Dumpcap 可用网卡
- 支持全部流量、ARP、ICMP、SSH、DNS、DHCP 等常用捕获过滤器，也可填写标准 BPF 过滤表达式
- 支持按持续时间、数据包数量或文件大小自动停止，至少需要启用一个停止条件
- 抓包在后台进程中运行，界面可随时手动停止
- 默认保存到 `%USERPROFILE%\Documents\AOMT_Captures`
- 文件格式为标准 `.pcapng`，结束后由 TShark 显示包数、字节数和持续时间，并可直接用 Wireshark 打开
- 自动分析协议分布、主要通信对象、Ping 应答、ARP 映射、STP 根桥、TCP 重传/复位和 DNS 错误
- “自动分析”和“运行日志”分开显示，抓包完成后自动切换到中文分析结论

使用前需单独安装 Wireshark 及其 Npcap 组件；项目不会将 Wireshark、Npcap、Dumpcap 或 TShark 打入 AOMT 安装包。普通电脑网卡只能捕获本机可见流量。要分析交换机其他端口的业务流量，需要先在交换机上配置端口镜像/SPAN，并将镜像目的端口连接到电脑抓包网卡。

### 常用配置模板

“常用配置模板”区域包含程序内置模板和用户自定义模板：

- 内置 H3C Comware 7 与 Huawei VRP V200 两套独立模板，不做跨品牌命令翻译
- 每个品牌提供开局基础、账号与 SSH/STelnet、Console、NTP 与日志、SNMPv3、Access 端口和 Trunk 端口配置
- 端口镜像抓包配置不作为内置模板提供
- 调用内置模板时先填写设备名称、地址、VLAN、账号等参数，并在发送前预览最终命令
- 密码字段不会写入模板文件、运行日志或结果记录；含密码的临时命令在任务结束后从内存清除
- RSA 本地密钥生成属于交互式命令，只作为人工前置步骤提示，不会自动批量发送
- 参数化模板只允许发送到对应品牌；设备声明品牌或连接后检测品牌不一致时会停止执行
- 调用模板后仍需手动点击“开始连接”才会执行
- 双击或调用内置模板可填写参数、查看脱敏预览并复制可执行命令
- 支持一次添加多个自定义模板文件
- 内置模板不能移除；移除自定义模板只删除列表记录，不删除原文件
- 自定义模板仍按普通文本文件原样发送，用户需自行确认命令、顺序和目标设备兼容性

自定义模板列表保存在：

```text
config/operation_templates.json
```

该文件属于本地运行数据，不提交到 Git。

### 日志管理

- 右侧实时显示连接及命令执行过程
- 日志默认字体为 16pt
- 左侧提供“查看日志”和“清空日志”
- 清空日志只清除界面内容，不删除磁盘日志

SSH 日志目录：

```text
logs/success/
logs/failure/
```

## 界面布局

默认窗口大小：

```text
2560 x 1600
```

顶部显示程序名称、版本和作者。主界面分为左右两个区域：

- 左侧：添加设备、Excel、脚本、操作、常用运维工具和配置模板
- 右侧：设备列表和连接日志

左右区域默认比例约为 `30% / 70%`，可拖动调整；左侧宽度不超过窗口的 50%。窗口高度不足时，左侧区域使用滚动条，表单内容不会被压缩。

## 环境要求

推荐环境：

- Windows 10 / 11
- Python 3.11

主要依赖：

- PyQt5 5.15.11
- paramiko 3.5.0
- openpyxl 3.1.5
- cryptography 46.0.7
- ntc-templates 9.2.0
- Pillow 11.3.0
- Nuitka 4.1.3

## 安装与启动

### 1. 克隆项目

```bash
git clone https://github.com/YiLanTinYu/SSH_Connection.git
cd SSH_Connection
```

### 2. 创建虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD：

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. 安装依赖

```bash
python -m pip install -r requirements.txt
```

### 4. 启动

```bash
python main.py
```

PyCharm 应选择当前项目解释器：

```text
<项目目录>\.venv\Scripts\python.exe
```

## Excel 使用说明

### 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 建议必填 | 设备名称；按设备匹配脚本时必须唯一且非空 |
| `group` | 否 | 设备分组，例如 `核心交换机` |
| `tags` | 否 | 逗号分隔标签，例如 `机房A,核心` |
| `brand` | 否 | 品牌，留空时默认为 `h3c` |
| `ip` | 是 | IPv4 或 IPv6 地址 |
| `port` | 否 | SSH 端口，默认 `22` |
| `username` | 是 | SSH 用户名 |
| `auth_method` | 否 | `password` 或 `key`，默认 `password` |
| `password` | 条件必填 | 密码认证时填写，可使用 AOMT 加密密文 |
| `private_key_path` | 条件必填 | 私钥认证时填写；相对路径以 Excel 所在目录为基准 |
| `private_key_passphrase` | 否 | 私钥口令，可使用 AOMT 加密密文 |
| `host_key_policy` | 否 | `tofu`、`strict` 或 `insecure`，默认 `tofu` |

### 创建加密 Excel

1. 按模板填写设备信息
2. 点击“加密 Excel 密码”
3. 选择原始 Excel
4. 输入并确认主密码
5. 选择加密文件保存位置
6. 使用生成的 `_encrypted.xlsx` 文件导入

建议确认加密文件可正常导入后，再安全处理原始明文文件。

加密操作会同时处理 `password` 和 `private_key_passphrase` 列中的非空明文。

### 导入设备

1. 点击“导入 Excel 文件”
2. 选择设备表
3. 如果是加密表，输入主密码
4. 如果是明文表，确认安全警告
5. 查看新增、重复和失败统计

## 设备筛选与结果中心

设备列表上方支持名称、IP、品牌、分组和标签搜索，并可按分组过滤。执行前可选择“全部设备”“筛选结果”或“选中设备”。

任务结束后点击“执行结果中心”，可逐台查看完整命令输出、开始与结束时间、耗时和错误，并导出 Excel、CSV 或 JSON。

## 命令文件格式

```text
# 以 # 开头的行是注释
display version
display interface brief
display vlan
```

规则：

- 每行一条命令
- 空行自动忽略
- `#` 开头的行自动忽略
- 文件编码建议使用 UTF-8
- 建议优先使用查询命令进行测试

## 五台设备测试数据

项目提供按设备同名脚本测试数据：

```text
test_data/五台交换机同名脚本测试设备.xlsx
test_data/per_device_scripts/
```

预期匹配：

```text
SW10 -> SW10.txt
SW20 -> SW20.txt
SW30 -> SW30.txt
SW40 -> SW40.txt
SW50 -> SW50.txt
```

测试表中的账号密码为虚拟数据。没有对应 SSH 服务器时，连接失败属于正常现象。

## Nuitka 打包

### 推荐：目录版

```bat
build.bat
```

构建脚本会自动在以下纯 ASCII 路径创建隔离构建环境，避免中文项目路径导致 GCC/SCons 编译失败：

```text
%LOCALAPPDATA%\AOMT_Nuitka_Build
```

源码、构建虚拟环境、Nuitka 缓存和中间产物都位于该目录；成功后，最终产物自动复制回项目的 `dist`。首次构建需要下载编译器并完整建立缓存，因此耗时较长。

输出：

```text
dist\main.dist\H3C_SSH_Tool.exe
```

目录版运行时必须保留整个 `main.dist` 文件夹，不能只复制 EXE。目录版通常启动更快，也更不容易被安全软件误报。

### 单文件版

```bat
build.bat onefile
```

输出：

```text
dist\H3C_SSH_Tool.exe
```

单文件版可以只复制 EXE，但启动时会释放运行文件，某些安全软件可能产生误报。建议先使用目录版测试。

### 调试打包

```bat
build.bat debug
```

调试版保留控制台窗口，适合排查无法启动的问题。程序启动异常时还会在运行目录生成：

```text
startup_error.log
```

## 测试

运行自动测试：

```bash
pytest -q
```

检查 Python 文件是否可以编译：

```bash
python -m compileall -q main.py core config ui utils tests
```

当前自动测试共 109 项，覆盖设备导入校验、重复设备、密码与私钥口令加密、SSH 私钥参数、Host Key 策略、本地 SSH 握手与 H3C Shell、交互式 SSH PTY、交互收发与尺寸同步、终端输出合并刷新、设备光标恢复、终端缩放内容保持、终端复制粘贴与选区保持、VT100 光标与 ANSI 颜色、串口回环收发、串口后台线程、串口实时状态检测、端口打开与异常关闭状态、串口占用错误提示、Console 单 CR 回车、旧串口配置迁移、双输入区键盘输入、鼠标焦点与互斥、FTP/TFTP 本地上传下载、IPv4/IPv6 文件传输命令提示、文件传输窗口、Wireshark 路径与网卡解析、Dumpcap 安全参数、抓包窗口及中文自动分析、H3C/Huawei 巡检模板解析、巡检方案存储与命令约束、参数化配置模板、敏感参数脱敏、CIDR 网段 Ping、IP/MAC 定位、接口诊断、连接与任务耗时拆分、结果中心窗口控制、连接配置、运维目标手工输入及合并去重、分组标签、配置备份规范化与元数据、结果导出、业务命令原样执行、脚本匹配、保存确认和任务取消等核心逻辑。

## 项目结构

```text
SSH_Connection/
├── config/
│   ├── app_info.py
│   ├── device_commands.py
│   ├── device_config.py
│   └── ssh_security.py
├── core/
│   └── ssh_manager_simple.py
├── ui/
│   ├── main_window.py
│   ├── result_dialog.py
│   ├── serial_console.py
│   ├── ssh_console.py
│   └── terminal_widget.py
├── utils/
│   ├── ipv6_utils.py
│   ├── logger.py
│   ├── maintenance_tools.py
│   ├── password_crypto.py
│   ├── result_export.py
│   └── serial_tools.py
├── tests/
│   ├── test_device_import_and_commands.py
│   ├── test_maintenance_tools.py
│   ├── test_maintenance_workers.py
│   ├── test_security_groups_results.py
│   └── test_serial_tools.py
├── test_data/
│   ├── per_device_scripts/
│   └── 五台交换机同名脚本测试设备.xlsx
├── docs/
├── Kylin/
├── main.py
├── SSH_command.txt
├── device_template.xlsx
├── create_icon.py
├── build.bat
├── requirements.txt
└── README.md
```

## 本地运行数据

以下目录或文件由程序运行时生成，不应提交敏感内容：

```text
logs/
config/operation_templates.json
.venv/
__pycache__/
.pytest_cache/
dist/
build/
```

## 安全说明

- 优先使用“加密 Excel 密码”功能，不要长期保留明文设备表
- 不要把主密码写入 Excel、脚本、README 或日志
- 不要把包含真实凭据的 Excel 提交到 Git
- 程序不会在日志中输出设备密码
- 默认 `tofu` 模式首次记录 Host Key，以后发现变化时拒绝连接
- `strict` 模式只允许系统或 AOMT 已知主机文件中已有的 Host Key
- `insecure` 模式不校验未知 Host Key，仅用于隔离测试环境
- AOMT 已知主机文件位于 `%LOCALAPPDATA%\AOMT\known_hosts`
- 建议使用最小权限运维账号
- 配置下发前先核对设备名称和脚本预览
- 勾选“执行后保存配置”前应先在少量设备上验证

## 版本信息

```text
版本：v1.0.0
作者：YiLanTinYu
```

这是 AOMT 的第一版。
