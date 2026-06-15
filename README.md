# 交换机 SSH 自动化运维工具

> 面向网络运维人员的图形化交换机批量运维工具，支持 Excel 导入、多品牌 SSH 批量连接、品牌感知命令翻译、批量 Ping、日志记录和常用配置模板查阅。

## 项目简介

**交换机 SSH 自动化运维工具（AOMT）** 基于 Python + PyQt5 开发，用于统一管理多品牌交换机的 SSH 运维任务。运维人员可以通过图形界面导入设备、选择业务命令文件、批量连接交换机、查看实时日志，并把常用配置模板集中保存到工具里便于查阅。

适用场景：

- 网络设备日常巡检
- 批量执行交换机业务命令
- 快速检查设备连通性
- 二层上联口辅助探测
- 运维命令模板集中查阅

技术栈：

- Python 3.7+
- PyQt5
- paramiko
- openpyxl
- ThreadPoolExecutor
- Nuitka

## 主要功能

### 设备管理

- 手动添加设备，支持名称、品牌、IP、端口、用户名、密码
- Excel 批量导入设备
- 下载 Excel 导入模板
- 按 `IP + 端口` 自动跳过重复设备
- 支持 IPv4 和 IPv6 地址
- 设备列表支持移除选中和清空列表
- 移除设备、清空列表均有二次确认

### 多品牌支持

当前支持以下品牌：

| 品牌 | 说明 |
|------|------|
| H3C | Comware 系列 |
| Huawei | VRP 系列 |
| Ruijie | RGOS 系列 |
| Cisco | IOS / NX-OS 系列 |
| TP-Link | JetStream 等系列 |

工具连接设备后会尝试识别品牌和型号。如果识别不到，也会优先使用用户在设备列表中手动选择的品牌。

### 品牌感知命令翻译

业务命令文件可按 H3C / Huawei 风格编写。连接不同品牌设备时，工具会自动转换为目标品牌等价命令。

示例：

```text
display interface brief  -> Cisco / Ruijie: show ip interface brief
display vlan             -> Cisco: show vlan brief
display arp              -> Cisco: show arp
```

默认命令文件为项目根目录下的 `SSH_command.txt`。

### 批量连接

- 多线程并发连接设备
- 默认最多同时连接 5 台设备
- 实时显示连接日志
- 设备列表状态列实时更新
- 连接完成后显示中文统计结果
- 可选执行后保存配置
- 可选探测二层上联口

### 常用运维工具

左侧提供 **常用运维工具** 区块。

当前包含：

- **批量 Ping**

批量 Ping 使用当前设备列表中的 IP，不需要再次导入 Excel。任务执行时会自动去重，结果以中文显示在连接日志窗口中。

任务完成后会生成日志文件：

```text
logs/pingYYYYMMDDHHMM.log
```

### 常用配置模板

左侧提供 **常用配置模板** 区块，用于集中保存常见配置命令文件。

支持功能：

- 多文件批量添加模板
- 双击模板查看内容
- 移除选中模板
- 移除模板只从列表中删除记录，不删除源文件

模板列表保存在本地运行配置：

```text
config/operation_templates.json
```

该文件属于本地使用数据，已加入 `.gitignore`，不会提交到仓库。

### 日志管理

- 右侧连接日志实时显示任务进度
- 日志字体默认 16pt
- 日志和弹窗统计均使用中文显示
- 左侧操作区提供 **查看日志** 和 **清空日志**
- 清空日志只清空界面显示，不删除日志文件

SSH 连接日志目录：

```text
logs/success/
logs/failure/
```

## 界面布局

程序默认窗口大小：

```text
2560 x 1600
```

左侧为操作区域：

- 添加设备
- 批量导入
- 业务命令文件
- 操作
- 常用运维工具
- 常用配置模板

右侧为工作区域：

- 设备列表
- 连接日志

左右区域可拖动调整宽度，左侧最大宽度不超过窗口宽度的 50%。窗口高度不足时，左侧区域会滚动，不会压缩表单内容。

## 安装说明

### 克隆项目

```bash
git clone https://github.com/YiLanTinYu/SSH_Connection.git
cd SSH_Connection
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动程序

```bash
python main.py
```

## 使用方法

### 1. 添加设备

可以手动添加设备：

1. 输入设备名称，例如 `SW1`
2. 选择品牌
3. 输入 IP 地址
4. 输入端口，默认 `22`
5. 输入用户名和密码
6. 点击 **添加设备**

也可以通过 Excel 批量导入：

1. 点击 **下载 Excel 模板**
2. 按模板填写设备信息
3. 点击 **导入 Excel 文件**
4. 导入完成后查看结果弹窗

Excel 字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| `ip` | 是 | 设备 IP 地址 |
| `username` | 是 | SSH 用户名 |
| `password` | 是 | SSH 密码 |
| `brand` | 否 | 品牌，默认 h3c |
| `port` | 否 | SSH 端口，默认 22 |
| `name` | 否 | 设备名称 |

### 2. 准备命令文件

默认使用项目根目录的：

```text
SSH_command.txt
```

命令文件规则：

- 每行一条命令
- `#` 开头的行视为注释
- 建议按 H3C / Huawei 风格编写命令

也可以在界面中点击 **选择文件** 使用自定义命令文件，或点击 **恢复默认** 回到 `SSH_command.txt`。

### 3. 开始连接

1. 确认设备列表无误
2. 根据需要勾选 **执行后保存配置**
3. 根据需要勾选 **探测二层上联口**
4. 点击 **开始连接**
5. 在右侧连接日志查看实时结果

### 4. 批量 Ping

1. 先把设备加入设备列表
2. 点击 **批量 Ping**
3. 查看右侧连接日志中的中文结果
4. 任务完成后查看生成的 `logs/pingYYYYMMDDHHMM.log`

### 5. 配置模板

1. 点击 **添加模板**
2. 可一次选择多个模板文件
3. 双击模板可查看内容
4. 点击 **移除选中** 可从列表移除模板记录

## 打包说明

Windows 下可使用 Nuitka 打包为独立 EXE。

推荐方式：

```bat
build.bat
```

手动方式：

```bat
python -m pip install -r requirements.txt
python -m nuitka --standalone --onefile --assume-yes-for-downloads --mingw64 --enable-plugins=pyqt5 ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=app.ico ^
  --include-data-files=SSH_command.txt=SSH_command.txt ^
  --include-data-files=device_template.xlsx=device_template.xlsx ^
  --output-dir=dist ^
  --output-filename=H3C_SSH_Tool.exe ^
  main.py
```

打包输出目录：

```text
dist/
```

## 项目结构

```text
SSH_Connection/
├── config/
│   ├── device_commands.py
│   └── device_config.py
├── core/
│   ├── ssh_manager.py
│   └── ssh_manager_simple.py
├── ui/
│   └── main_window.py
├── utils/
│   ├── ipv6_utils.py
│   └── logger.py
├── tests/
│   └── test_device_import_and_commands.py
├── docs/
├── Kylin/
├── main.py
├── SSH_command.txt
├── device_template.xlsx
├── build.bat
├── requirements.txt
└── README.md
```

## 运行数据

以下内容为运行时生成或本地环境文件，不纳入 Git：

```text
logs/
config/operation_templates.json
.venv/
__pycache__/
dist/
build/
```

## 安全说明

- 密码仅在内存中用于 SSH 登录
- 日志中不记录设备密码
- 建议使用最小权限运维账号
- 批量操作前建议先在少量设备上验证命令文件

## 当前版本

```text
v1.0.0
```

这是当前 GitHub 仓库的第一版。
