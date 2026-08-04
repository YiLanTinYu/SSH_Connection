# AOMT 项目交接上下文

## 1. 项目基本信息

- 项目名称：AOMT（交换机自动化运维工具）
- 当前版本：v1.0.0
- 作者：YiLanTinYu
- 当前项目目录：`C:\运维小工具\交换机运维工具`
- GitHub 仓库：`git@github.com:YiLanTinYu/SSH_Connection.git`
- 默认分支：`main`
- 技术栈：Python 3.11、PyQt5、Paramiko、PySerial、OpenPyXL、Cryptography、Pillow、Nuitka

AOMT 是面向网络运维人员的 Windows 图形化工具，用于批量管理多品牌交换机的 SSH 运维任务。

## 2. 已确认需求

### 2.1 设备与界面

- 支持手动添加设备和 Excel 批量导入。
- 设备字段包括名称、分组、标签、品牌、IP、SSH 端口、用户名和认证设置。
- 支持密码认证和 SSH 私钥认证。
- 支持设备搜索、分组过滤，以及全部/筛选结果/选中设备三种执行范围。
- 支持 IPv4 和 IPv6。
- 设备按 `IP + 端口` 去重。
- 移除选中设备、清空设备列表和清空日志均需二次确认。
- 日志默认字体为 16pt，其余主要界面字体在原基础上放大。
- 左右区域可拖动，默认比例约为 `30% / 70%`。
- 左侧宽度不得超过主界面的 50%。
- 窗口高度不足时左侧区域滚动，不能压缩添加设备表单。
- 默认窗口大小为 `2560 x 1600`。
- 界面显示版本 `v1.0.0` 和作者“倚栏听雨”。
- 主界面采用紧凑运维控制台风格，使用统一的 Lucide 线性图标、深青色导航与日志区、白色数据工作区、蓝色主要操作和珊瑚色危险提示。
- 同类按钮、表格、输入框、滚动条与焦点状态必须保持统一，工具按钮不得重新混用 Emoji 作为主图标。

### 2.2 SSH 与脚本

- 用户入口仅支持 H3C/Comware 和 Huawei/VRP；Excel、JSON 导入会拒绝其他品牌。
- 连接后尝试识别设备品牌和型号。
- 用户业务命令严格按脚本原文发送，不进行自动翻译或改写。
- 不同品牌或系统版本存在命令差异时，应使用自定义文件或按设备匹配模式。
- 默认最多并发连接 5 台设备。
- 支持运行中停止批量连接任务。
- 支持执行后保存配置。
- 支持二层上联端口辅助探测。
- 连接过程、命令执行及最终统计使用中文显示。
- 按设备保留完整命令输出、错误、开始结束时间和耗时，并支持导出。

业务命令有两种模式：

1. 统一脚本：全部设备执行同一个 TXT，默认使用 `SSH_command.txt`。
2. 按设备匹配：只使用设备名称匹配同名 TXT。

按设备匹配规则已经确认：

```text
设备名称 SW_CORE_01 -> SW_CORE_01.txt
```

- 不按 IP 匹配。
- 不按品牌匹配。
- 不使用 `default.txt` 回退。
- 不再使用 Excel 的 `script_file` 字段。
- 未找到同名脚本时跳过该设备。
- 执行前显示设备与脚本的匹配预览。

### 2.3 Excel 密码安全

- Excel 可以包含明文密码，但导入时必须显示安全警告。
- 界面提供“加密 Excel 密码”功能。
- 使用 AES-256-GCM 加密设备密码。
- 使用 PBKDF2-SHA256 和随机盐从主密码派生密钥。
- 主密码至少 8 个字符。
- 主密码不得写入 Excel、日志或配置文件。
- 导入加密 Excel 时提示输入主密码。
- 主密码错误或密文损坏时拒绝解密。
- 加密文件可以复制到其他电脑使用，但必须提供相同主密码。
- 主密码丢失后不能恢复设备密码。
- 私钥口令与设备密码使用同一密文格式和主密码保护。

密文格式版本前缀：

```text
AOMT_ENC_V1$
```

### 2.4 辅助功能

- 批量 Ping 支持设备列表、手工地址和 CIDR 网段三种目标来源，不单独导入文件；IPv4 网段排除网络地址和广播地址，合并后单次限制 4096 个目标。
- 批量 Ping 最多使用 32 路受控并发，网段展开结果与其他目标合并去重。
- Ping 结果在连接日志区域以中文显示。
- Ping 完成后生成 `ping年月日时分.log`，重名时自动追加序号。
- 批量 TCP 端口检测支持用户指定端口，默认 `22,23,80,443`。
- SSH 登录测试只验证认证，不打开设备 Shell，不执行设备命令。
- 批量路由跟踪复用设备列表并生成中文日志。
- 配置对比支持常见文本编码、统一差异显示及结果保存。
- 配置备份使用品牌对应的只读当前配置查询命令；每台设备使用独立目录，配置正文保存为版本化 UTF-8 `.cfg`，同名 `.json` 保存非敏感元数据和 SHA-256；无效或空输出不生成文件。
- 一键设备巡检使用各品牌明确的只读命令采集 H3C/Comware、Huawei VRP 的 CPU、内存、温度、风扇、电源、接口摘要和硬件信息；内置项目可勾选，支持按品牌增加自定义 `display` 查询命令并保存方案。
- 巡检方案保存在 `%LOCALAPPDATA%\AOMT\health_check_profiles.json`；标准巡检不可覆盖或删除，自定义命令只展示原始输出，不参与健康判定。
- IP/MAC 终端定位采用 IPv4 → ARP → MAC 地址表 → 交换机接口流程；当前支持 H3C/Comware、Huawei VRP 和 IPv4/MAC 查询。
- 接口综合诊断读取 H3C、Huawei 接口状态、速率、双工、链路类型、PVID及光模块诊断/告警输出。
- 三个设备诊断工具支持设备列表/Excel 目标与手工 SSH 目标，后台并发执行，结构化结果可导出 Excel、CSV 或 JSON。
- 诊断解析复用 NTC Templates 9.2.0、NAPALM H3C Comware 模板，并参考 NAPALM Huawei VRP 的环境采集实现；来源和许可证记录在 `THIRD_PARTY_NOTICES.md`。
- H3C 与 Huawei 诊断必须使用独立品牌命令，不做自动翻译；检测到其他品牌时必须停止并提示。
- 配置正文会清理 ANSI 控制符、分页提示、查询命令回显和独立设备提示符；元数据不得保存用户名、密码或私钥口令。
- 主界面左侧按职责分为“设备库、设备作业、本机工具、模板中心”四页；右侧保留设备列表、连接日志和结果中心。
- 业务命令、Ping、端口检测、SSH 登录测试、路由跟踪、巡检、定位、接口诊断和配置备份统一复用“设备作业”的共享目标范围。
- 共享目标范围支持全部设备、筛选结果、设备表选中行和临时自定义目标；临时目标可输入 IPv4、IPv6、主机名及 SSH 凭据，合并后自动去重。
- 共享目标中的 CIDR 网段只供批量 Ping 使用，不进入 SSH、巡检、备份和配置任务。
- 串口控制台、文件传输、网络抓包、子网计算和配置对比归入“本机工具”，不依赖设备库。
- 子网计算器支持 IPv4 和 IPv6。
- 批量网络工具使用后台线程，不阻塞主界面。
- 常用配置模板分为程序内置模板和用户自定义模板。
- 内置模板按 H3C Comware 7 和 Huawei VRP V200 分开提供开局基础、账号与 SSH/STelnet、Console、NTP 与日志、SNMPv3、Access 和 Trunk 配置，不提供端口镜像抓包模板。
- 内置模板采用参数表单和脱敏预览；密码不落盘、不进入日志或结果，含密码的临时命令在任务结束后从内存清除。
- RSA 本地密钥生成作为人工前置步骤提示，不自动批量发送；参数化模板遇到品牌不匹配时必须停止执行。
- 自定义配置模板支持多文件导入、双击查看和按需调用。
- 移除自定义模板只删除列表记录，不删除源文件。
- SSH 成功、失败日志分别保存。
- 常用运维工具包含独立的串口控制台，支持 Windows COM 端口扫描和交互。
- 串口控制台支持波特率、数据位、校验、停止位、流控、编码、行结束符和 DTR/RTS；交换机 Console 默认使用单 CR 回车。
- 串口控制台支持常用控制键、隐藏输入、清屏、会话日志和连接配置保存。
- 深色串口终端区可直接捕获键盘输入并发送，设备回显负责显示输入内容。
- 深色终端和下方命令框使用互斥输入模式，焦点所在区域显示光标并独占键盘输入。
- 串口读取必须运行在后台线程，不能阻塞主界面。
- 串口界面只能声明 COM 端口是否已打开，不能把“端口已打开”表述成设备在线；设备断电但 USB 串口仍存在时状态显示“设备状态未知”，端口读写错误后的关闭状态必须保留异常提示。
- 串口打开后每 2 秒检查一次适配器枚举、串口句柄和可用线路信号；适配器消失后停止当前会话并每 1 秒检查恢复情况，恢复后提示用户手动重新打开，不自动发送探测字符或自动重连。
- CTS、DSR、CD、RI 等线路信号仅作为提示信息，不能据此笼统断言交换机在线；未接对应信号线或适配器不支持时应明确显示设备状态未知。
- 串口和 SSH 交互窗口共用基于 pyte 的 VT100/ANSI 终端控件。
- 终端高频输出采用短周期合并刷新，并按连续文本样式批量绘制，避免大量输出时频繁全量重绘造成输入卡顿。
- 终端记录设备端真实光标位置；普通点击只切换输入焦点并恢复设备光标，拖动选择文本仍可用于复制。
- 终端缩放不得直接使用 pyte 0.8.2 的纵向裁剪逻辑；缩小时需把移出屏幕的顶部行转入历史并保持光标处于有效行，横向缩窄时保留暂时不可见的单元格。
- 串口和 SSH 共用终端右键菜单；有选区时 Ctrl+C 复制，无选区时发送中断，Ctrl+V/Ctrl+Shift+V 粘贴并发送；输出刷新时尽量保持现有选区。
- SSH 交互终端的设备框同时支持下拉和输入：可选择手工添加或 Excel 导入的现有设备，也可覆盖输入地址、端口、用户名和密码；选择现有设备时复用其认证和 Host Key 策略。
- SSH 交互终端只建立原始交互 Shell，不自动执行品牌识别、禁分页或业务脚本。
- 常用运维工具包含独立的 FTP/TFTP 文件传输窗口，支持监听地址、端口、共享目录、FTP 临时凭据、被动端口和上传权限配置。
- FTP/TFTP 服务必须在后台线程运行，窗口关闭时自动停止；默认只读，未经用户勾选不得接受交换机上传。
- 文件传输窗口只展示 H3C 参考命令，不自动向设备发送；TFTP/FTP 均为明文协议，只允许在可信的隔离运维网络中临时使用。
- 常用运维工具包含网络抓包窗口，调用用户单独安装的 Wireshark Dumpcap/TShark，不内置或分发 Wireshark/Npcap。
- 抓包支持网卡选择、BPF 过滤、持续时间/包数/文件大小限制、手动停止、TShark 中文自动分析和使用 Wireshark 打开 `.pcapng`。
- 自动分析覆盖协议分布、主要 IP 通信、ICMP 请求/应答、ARP 映射、STP 根桥/拓扑变化、TCP 重传/缺失段/复位及 DNS 错误响应。
- 普通网卡只能看到本机可见流量；分析交换机其他端口时，需要用户预先配置端口镜像/SPAN。

## 3. 现有功能状态

已实现并经过自动测试的主要功能：

- Excel 必填字段、IP 和端口校验
- 重复设备过滤
- 明文 Excel 安全提示
- Excel 密码加密、解密和错误主密码校验
- SSH 私钥认证参数和 Host Key 策略
- 设备分组、标签、搜索和执行范围
- 按设备执行结果中心及 Excel/CSV/JSON 导出
- 串口控制台、虚拟回环收发和本地连接配置
- pyte 终端光标、ANSI 样式、键盘序列和交互式 SSH PTY
- 用户业务命令原样执行
- 只按设备名称匹配脚本
- 执行前脚本匹配预览
- SSH 并发处理和停止机制
- 保存配置交互确认处理
- 中文运行日志和结果统计
- 批量 Ping 及日志文件
- 批量端口检测、SSH 登录测试和路由跟踪
- 配置备份与本地配置文件对比
- Wireshark/Dumpcap 网络抓包和 `.pcapng` 保存
- IPv4/IPv6 子网计算
- 常用配置模板管理
- 应用图标、版本和作者显示
- Nuitka 打包脚本

## 4. 运行环境

推荐：

```text
Windows 10 / 11
Python 3.11
```

虚拟环境：

```text
C:\运维小工具\交换机运维工具\.venv\Scripts\python.exe
```

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动：

```powershell
python main.py
```

PyCharm 迁移后应重新选择新目录下的 `.venv\Scripts\python.exe`，不要继续使用旧目录或已经删除的 Anaconda 解释器。

## 5. 构建方法

项目路径包含中文，不能直接在项目目录中调用旧版 Nuitka/GCC 编译。当前 `build.bat` 使用：

```text
%LOCALAPPDATA%\AOMT_Nuitka_Build
```

作为纯 ASCII 隔离构建目录，并使用独立虚拟环境。当前构建依赖包括 Pillow 11.3.0 和 Nuitka 4.1.3。完成后产物自动复制回项目 `dist`。

### 5.1 推荐目录版

```bat
build.bat
```

输出：

```text
dist\main.dist\H3C_SSH_Tool.exe
```

目录版必须连同整个 `main.dist` 文件夹一起复制。

### 5.2 单文件版

```bat
build.bat onefile
```

输出：

```text
dist\H3C_SSH_Tool.exe
```

单文件版启动时会释放临时运行文件，安全软件误报概率通常高于目录版。

### 5.3 调试版

```bat
build.bat debug
```

调试版保留控制台。程序启动失败时还会尝试生成：

```text
startup_error.log
```

## 6. 测试情况

迁移到新目录后已执行：

```powershell
pytest -q
```

最近结果：

```text
211 passed
```

编译检查：

```powershell
python -m compileall -q main.py core config ui utils tests
```

最近结果：通过。

自动测试主要覆盖：

- Excel 导入校验
- 重复设备
- 密码加密与解密
- 错误主密码
- 业务命令原样执行
- 同名脚本匹配
- 非法 IPv4 过滤
- 保存配置确认
- 连接结果状态
- 任务取消
- 私钥认证参数
- TOFU 与严格 Host Key 策略
- 本地 Paramiko SSH 握手与 H3C 命令行模拟
- PySerial `loop://` 字节回环、后台线程和串口档案
- pyte VT100 光标覆盖、ANSI 颜色和键盘控制序列
- Paramiko 交互式 SSH PTY 建立、尺寸参数和数据接收
- 分组标签和新版 Excel 字段
- 执行结果脱敏与三种格式导出
- FTP/TFTP 本机回环上传、下载、权限、端口和服务停止
- 文件传输窗口以及 H3C IPv4/IPv6 参考命令
- Wireshark 路径和网卡解析、Dumpcap 参数约束、抓包窗口、中文自动分析与工具顺序
- 完整提示符识别，百分比结尾的 CPU/利用率输出不会被误判为提示符
- H3C S6850 与 Huawei S5720 实际巡检输出的保守解析回退
- 统一执行前预览、命令脱敏、高风险命令识别和显式确认
- SQLite 批量执行审计历史、脚本指纹和凭据不落库
- 发布前生成文件与敏感文件检查

2026-07-31 已使用加密设备表完成 5 台 H3C 模拟交换机和 1 台 Huawei 真机只读巡检：

- 6 台设备全部 SSH 登录成功，品牌识别全部匹配。
- 5 台 H3C 均识别为 S6850，IPv4/IPv6 登录和 7 类巡检命令均成功。
- Huawei 真机识别为 S5720-28X-SI-AC Routing Switch，7 类巡检命令均成功。
- 修复华为 CPU 百分比输出被误判为终端提示符而导致命令输出串行错位的问题。
- H3C 代表设备成功结构化 CPU、内存、6 项温度、2 项风扇、2 项电源、61 个接口和 3 项制造信息。
- Huawei 代表设备成功结构化 CPU、内存、温度、风扇、2 项电源、31 个接口和 2 项硬件信息。
- Huawei SSH 握手约 14.5 秒；Windows OpenSSH 对照测试耗时相同，延迟来自设备侧 SSH/AAA 路径。
- 全程仅执行分页控制、`display version` 和只读 `display` 巡检命令，未进入配置视图、未保存配置。
- 人工界面验收中，批量 Ping、TCP/22 端口检测和 SSH 登录测试均为 6/6 成功，IPv4/IPv6 混合目标正常，中文日志按时间戳生成。
- 修复 SSH 登录测试将统一 30 秒超时错误覆盖为 10 秒的问题；Huawei 实机复测约 14 秒后认证成功。
- 修复 Huawei 温度摘要使用错误命令键的问题；S5720 实机成功解析最高温度，巡检摘要共 7 类结构化指标。
- 6 台配置备份均成功生成版本化 `.cfg` 与 `.json`；修复 Windows 换行转换造成元数据 SHA-256 与实际文件不一致的问题，SW52 实机复测哈希、行数和终端清理均通过。
- 完成主窗口第一阶段拆分：主题与样式、分隔条、品牌横幅、状态徽章以及三个后台工作线程均已独立成模块。
- 第二阶段已拆出图标工厂、通用对话框、设备表格 Presenter、设备管理、作业目标、运维任务、配置模板、批量执行、执行结果和菜单构建模块；随后继续拆出右侧设备工作区、目标设备面板、业务命令文件面板、批量执行面板、设备工具面板、本机工具面板、添加设备表单、Excel 导入面板、列表管理面板和配置模板面板。
- 第三阶段已将维护任务、设备清单与共享目标、配置模板和批量 SSH 生命周期迁移到独立控制器，并拆出配置对比、子网计算器、状态栏、日志格式化和响应式布局计算。
- 第四阶段新增工具窗口调度器、主窗口通用动作控制器和组合式布局构建器；`main_window.py` 当前约 2028 个非空行（2260 个物理行），继续保留 128 个兼容方法入口，作为各 UI 面板的编排层。
- 每完成一个模块迁移均执行定向测试和完整回归；当前自动测试为 `211 passed`。`pyftpdlib` 已升级到 2.2.0；Python 3.11 下仍会报告 `asyncore/asynchat` 两条弃用警告，Python 3.12+ 会由该依赖声明的 `pyasyncore`、`pyasynchat` 兼容包接管。

2026-08-03 已使用一台离线维护的 H3C S5048PV5-EI（Comware 7.1.070 Release 6380）完成真实设备补充验证：

- 使用一次性隐藏凭据弹窗连接，账号密码只保存在进程内，测试结束后未写入文件或日志。
- 项目 Paramiko 连接、H3C 品牌识别和 `display version` 只读命令通过；设备仅提供旧式 `ssh-rsa` 主机密钥时，项目连接栈仍可正常协商。
- 正式配置备份流程成功生成 741 行、7788 字节的 UTF-8 `.cfg` 与无凭据 `.json` 元数据；SHA-256、行数、结束标记、分页清理和提示符清理均通过。
- 在不执行保存命令的前提下，临时创建 VLAN 4093、读取验证并删除成功；测试前后当前配置与启动配置各自哈希保持一致。
- 在只读配置输出过程中主动中断 SSH 会话后，可重新连接并继续执行只读命令，最终配置复核通过。
- 未执行真实 `save force`：测试前发现当前配置与启动配置存在有效命令差异，保护逻辑在写入前停止，避免把临时维护配置固化到启动文件。
- 真实配置备份和差异诊断文件仅保存在仓库外的用户文档备份目录，不得复制进项目或提交 Git。

2026-07-30 已使用本机 Wireshark 4.6.7 在 NPF Loopback 网卡完成真实抓包验证：

- Dumpcap 自动停止抓包成功，TShark 可读取生成的 `.pcapng`
- 4 秒 ICMP/ICMPv6 测试捕获 6 个数据包，无丢包
- 手动停止耗时约 0.01 秒，停止后文件仍可被 TShark 正常解析

2026-07-29 已使用 5 台 H3C 模拟交换机完成真实文件传输验证：

- SW10、SW20、SW40 使用 IPv4，SW30、SW50 使用 IPv6。
- 5 台设备的 TFTP 上传全部成功。
- 5 台设备的 FTP 登录、被动/扩展被动数据通道和上传全部成功。
- 测试读取设备已有 `startup.cfg` 并上传到电脑临时目录，没有向交换机写入文件。
- FTP 与 TFTP 收到的文件大小和 SHA-256 摘要一致，测试完成后已删除电脑上的临时配置副本。

真实交换机上的品牌差异、保存配置提示和长时间批处理仍应进行人工验证。

## 7. 关键目录与文件

```text
config/app_info.py                 程序名称、版本、作者
config/device_commands.py          品牌识别和命令映射
config/device_config.py            设备模型、Excel 导入导出
config/ssh_security.py             SSH 认证参数和 Host Key 策略
core/ssh_manager_simple.py         SSH 连接和批处理核心
services/device_management.py      手工添加设备校验与写入服务
services/task_targets.py           作业目标同步、过滤与摘要
services/maintenance_tasks.py      运维任务定义、统计与日志文件
services/config_templates.py       用户配置模板存储与读取
services/batch_execution.py        批量命令执行前参数准备
services/execution_results.py      连接结果归一化、统计与审计状态
services/log_formatting.py         主窗口日志地址规范化、转义与着色
controllers/                       设备、模板、维护、批量 SSH、工具窗口与通用动作控制器
ui/main_window.py                  PyQt5 主窗口编排与事件处理
ui/main_window_layout.py           主框架、品牌头、左右工作区和按钮装饰
ui/main_window_status.py           主窗口状态栏与进度显示
ui/responsive_layout.py            响应式字号、侧栏宽度与工具列计算
ui/config_diff_dialog.py           配置对比对话框
ui/subnet_calculator_dialog.py     IPv4/IPv6 子网计算器
ui/theme.py                        主题令牌与全局样式表
ui/splitter.py                     可拖动工作区分隔条
ui/aurora_header.py                顶部品牌横幅
ui/status_badge.py                 设备状态徽章
ui/connection_worker.py            批量 SSH 连接工作线程
ui/ping_worker.py                  批量 Ping 工作线程
ui/maintenance_worker.py           端口、登录、路由与备份工作线程
ui/icon_factory.py                 应用图标加载与备用绘制
ui/dialog_helpers.py               密码、警告与二次确认对话框
ui/device_table_presenter.py       设备表格刷新、筛选与范围选择
ui/main_menu.py                    主菜单创建与动作路由
ui/result_dialog.py                按设备执行结果中心
ui/serial_console.py               串口控制台窗口和读取线程
ui/file_transfer_dialog.py         FTP/TFTP 文件传输窗口
utils/file_transfer_service.py     FTP/TFTP 后台服务与传输事件
ui/packet_capture_dialog.py        Wireshark 网络抓包窗口
utils/packet_capture.py            Dumpcap/TShark 发现、抓包进程与结果统计
ui/ssh_console.py                  单设备 SSH 交互终端和连接线程
ui/terminal_widget.py              串口与 SSH 共用的 VT100/ANSI 终端控件
utils/ipv6_utils.py                IPv6 校验和处理
utils/logger.py                    日志管理
utils/maintenance_tools.py         常用网络诊断和本地计算
utils/password_crypto.py           Excel 密码加密
utils/result_export.py             执行结果导出
utils/serial_tools.py              串口发现、参数和连接配置存储
tests/test_device_import_and_commands.py
tests/test_maintenance_tools.py
tests/test_maintenance_workers.py
tests/test_security_groups_results.py
tests/test_serial_tools.py
SSH_command.txt                    默认统一命令文件
build.bat                          Nuitka 打包入口
README.md                          GitHub 项目简介
USER_GUIDE.md                      软件内详细使用说明
```

本地运行数据：

```text
logs/
config/operation_templates.json
dist/
build/
.pytest_cache/
__pycache__/
```

## 8. Git 当前状态

迁移时所在分支：

```text
main
```

迁移时远程仓库：

```text
origin  git@github.com:YiLanTinYu/SSH_Connection.git
```

迁移时最近提交：

```text
df277a8  Remove generated switch configuration files
```

当前工作区仍有未提交修改。已知包括：

- README 和项目结构文档更新
- 设备导入及业务命令执行修复
- SSH 取消、保存确认和任务状态修复
- 删除未使用的 `core/ssh_manager.py`
- 新增应用信息模块
- 新增 Excel 密码加密模块
- 新增按设备同名脚本功能
- 新增测试数据和测试用例

提交前必须先执行：

```powershell
git status --short
git diff --check
pytest -q
```

提交仓库前应清理以下可再生或临时内容：

```text
srbuild/
docs/ui_mockups/
preview_themes.py
```

`test_data/` 仅供本地验证并整体忽略，不得提交到 Git。

## 9. 安全与维护注意事项

- 不要把真实设备密码、主密码或生产设备表提交到 Git。
- 加密 Excel 的安全性依赖主密码强度。
- 日志不得输出设备密码或主密码。
- 默认使用 TOFU：首次记录 Host Key，后续不一致时拒绝连接。
- 严格模式要求 Host Key 已存在于系统或 `%LOCALAPPDATA%\AOMT\known_hosts`。
- 不校验模式仅应用于隔离测试环境。
- 串口档案只保存连接参数，不保存 Console 用户名或密码。
- 虚拟串口测试不能代替真实 USB 转串口线和 H3C Console 登录测试。
- 程序不会自动转换用户业务命令；配置下发前必须确认脚本适用于目标品牌和系统版本。
- 配置下发前必须核对设备名称、目标设备和脚本预览。
- 所有批量命令任务必须在统一预览窗口核对脱敏后的实际命令并显式确认。
- 批量执行审计库位于 `%LOCALAPPDATA%\AOMT\task_history.db`，不保存密码、私钥或完整命令输出。
- 创建发布版本前运行 `python release_check.py`，不得绕过敏感文件检查。
- “执行后保存配置”可能改变设备持久化配置，应谨慎启用。
- 保存配置提示符在不同品牌和版本中可能不同，新增设备型号时应回归测试。
- IPv6 地址不参与脚本文件匹配，脚本只认设备名称。
- UI 主文件仍是编排入口；新增功能应优先落在现有面板、控制器或服务模块中，避免重新堆回主文件。
- `core/ssh_manager.py` 已作为死代码删除，不应重新引入 Netmiko 依赖，除非明确决定恢复该架构。

## 10. 建议的后续工作

1. 待真实 H3C 设备的当前配置与启动配置完成核对并同步后，再验证 `save force` 持久化路径；临时写入、回滚和异常中断路径已通过。
2. 对未跟踪文件进行归类，清理确认无用的构建产物。
3. 审查全部未提交改动后形成一个清晰提交。
4. 推送 GitHub 前再次确认测试数据不包含真实凭据。
5. 后续考虑跳板机、连接重试、enable 密码和凭据库。
6. 新功能继续遵守视图、控制器、服务分层，并为每个行为补充定向测试和全量回归。
