# 多品牌自动识别功能：代码实现详解

> 本文档基于 `core/ssh_manager_simple.py` 和 `config/device_commands.py` 的真实代码，
> 用通俗语言解释每一个技术细节，适合编程新手阅读。

---

## 先澄清一个重要概念

**本项目的"多品牌识别"≠ 图像识别。**

图像识别（检测商标颜色、形状、Logo）用于识别快消品品牌（可口可乐、耐克等），
需要机器学习模型（如 CNN 卷积神经网络）。

本项目识别的是 **网络交换机的品牌**，设备没有摄像头，只有命令行。
工具通过 SSH 登录设备，让设备"自报家门"——发送 `display version` 命令，
然后在返回的**纯文本**中寻找品牌关键字。这是一种**文本特征匹配**，
不需要机器学习，但设计同样精妙。

---

## 一、整体流程图

```
SSH 登录成功
      │
      ▼
发送 display version          ← H3C / 华为 的命令语法
      │
      ├── 返回包含 "H3C" 或 "Comware" ──► 确认品牌 = h3c
      │
      ├── 返回包含 "Huawei" 或 "VRP"  ──► 确认品牌 = huawei
      │
      └── 返回 "Invalid command"（命令不存在）
              │
              ▼
        发送 show version      ← Cisco / 锐捷 / TP-Link 的命令语法
              │
              ├── 包含 "Cisco"  ──► 品牌 = cisco
              ├── 包含 "Ruijie" ──► 品牌 = ruijie
              └── 包含 "TP-Link"──► 品牌 = tplink
                      │
                      ▼
              还是没识别？回退到用户手动选择的品牌
```

---

## 二、"特征提取"：从文本中寻找品牌指纹

### 2.1 什么是"特征"？

不同品牌的交换机在 `display version` / `show version` 的输出中，
都会出现独一无二的文字标记，这就是**文本特征**：

```
# H3C 交换机返回的版本信息（节选）
H3C Comware Software, Version 7.1.049, Release 2612P06
H3C S5560-54C-EI uptime is 10 weeks, 3 days, ...
                 ^^^
                 这里有 "H3C" → 识别为 H3C 品牌

# 华为交换机返回（节选）
Huawei Versatile Routing Platform Software
VRP (R) software, Version 5.170 (S5735 V200R019C10SPC500)
^^^                             ^^^^^
"Huawei" 和 "VRP" → 识别为 huawei 品牌

# 思科交换机返回（节选）
Cisco IOS Software, Version 15.2(7)E5
cisco WS-C2960X-24TS-L (PowerPC405) processor
^^^^^
"Cisco" 和 "IOS" → 识别为 cisco 品牌
```

### 2.2 特征存储：品牌关键字字典

所有品牌的"特征指纹"集中存储在 `config/device_commands.py` 的 `BRAND_KEYWORDS`：

```python
# config/device_commands.py  第 16-24 行
BRAND_KEYWORDS = {
    'h3c':       ['h3c', 'comware'],          # H3C 设备特有关键字
    'huawei':    ['huawei', 'vrp'],           # 华为设备特有关键字
    'ruijie':    ['ruijie', 'rg-os'],         # 锐捷设备特有关键字
    'cisco':     ['cisco', 'ios', 'nx-os'],   # 思科设备特有关键字
    'tplink':    ['tp-link', 'tplink', 't2600', 'jetstream'],
}
```

**为什么要有多个关键字？**
同一品牌的不同型号，版本输出的措辞可能不同。
例如 H3C 企业级设备输出 `H3C`，但运营商级设备可能只输出 `Comware`，
所以每个品牌配置多个关键字，只要命中其中一个就算识别成功。

---

## 三、核心函数：`detect_brand()`

### 3.1 完整代码（带注释）

```python
# config/device_commands.py  第 193-230 行

def detect_brand(version_output: str) -> str:
    """根据版本命令的输出文本识别设备品牌"""

    # 防御：如果没有任何输出（超时/连接问题），默认按 H3C 处理
    if not version_output:
        return 'h3c'

    # 把所有字符转小写，避免大小写不同导致匹配失败
    # 例如 "H3C" 和 "h3c" 都能被 'h3c' 这个关键字匹配
    version_lower = version_output.lower()

    # 有序优先检查列表（顺序非常重要！）
    priority_checks = [
        ('h3c',    ['h3c', 'comware']),
        ('huawei', ['huawei', 'vrp']),
        ('ruijie', ['ruijie', 'rg-os']),
        ('tplink', ['tp-link', 'tplink', 'jetstream', 't2600']),
        ('cisco',  ['cisco', 'ios', 'nx-os']),   # cisco 放最后！
    ]

    for brand, keywords in priority_checks:
        # any() 相当于"多个 OR 条件"：
        # 关键字列表中只要有一个出现在输出中，就返回该品牌
        if any(kw in version_lower for kw in keywords):
            return brand

    # 所有关键字都没命中 → 兜底：按 H3C 处理
    return 'h3c'
```

### 3.2 为什么 Cisco 必须放在最后？

**顺序陷阱**：部分 H3C 设备的版本输出中包含 `IOS-like` 字样，
如果 `cisco` 的检查排在 `h3c` 前面，就会误把 H3C 设备识别为 Cisco。

```
# H3C 某型号输出（片段）
H3C Comware IOS-style interface command support
           ^^^
           如果先检查 'ios' 关键字 → 误判为 Cisco！
           所以 H3C 必须排在 Cisco 之前检查
```

这种"优先级排序"思路，在文本分类中叫**优先级规则匹配**。

---

## 四、两步识别机制：`_detect_brand_and_model()`

### 4.1 为什么需要两步？

不同品牌使用不同的命令语法：

| 品牌 | 查看版本命令 |
|------|------------|
| H3C / 华为 | `display version` |
| 思科 / 锐捷 / TP-Link | `show version` |

如果工具不知道设备品牌，就不知道该用哪个命令——这是一个**鸡生蛋/蛋生鸡**问题。
解决方法：**先用 H3C 命令试探，如果设备说"命令无效"，再换 Cisco 命令**。

### 4.2 完整代码（带注释）

```python
# core/ssh_manager_simple.py  第 213-244 行

def _detect_brand_and_model(self):
    """两步品牌识别"""

    # ── 第一步：用 H3C/华为 语法试探 ──────────────────────
    output = self.execute_command('display version')

    # 检查设备是否回报"命令无效"
    # H3C/华为 设备会执行命令并返回版本信息
    # Cisco 设备会返回 "% Invalid input detected"
    invalid = re.search(
        r'% Invalid|Unrecognized command|Error:',
        output or '',
        re.IGNORECASE  # 忽略大小写
    )

    # 没有报错 + 有输出内容 → 说明是 H3C 或华为设备
    if not invalid and output and output.strip():
        brand = detect_brand(output)         # 进一步确认是 h3c 还是 huawei
        if brand in ('h3c', 'huawei'):
            self.brand_detected = brand
            self.model_detected = self._extract_model(output, brand)
            return                           # 识别成功，直接退出

    # ── 第二步：换 Cisco/锐捷/TP-Link 语法重试 ───────────
    output2 = self.execute_command('show version')
    if output2 and output2.strip():
        brand = detect_brand(output2)
        self.brand_detected = brand
        self.model_detected = self._extract_model(output2, brand)
        return

    # ── 兜底：使用用户在界面上手动选择的品牌 ──────────────
    self.brand_detected = (
        getattr(self.device_info, 'brand', 'h3c') or 'h3c'
    ).lower()
```

### 4.3 流程示意

```
工具连接未知品牌设备
        │
        ▼
发送 "display version"
        │
   ┌────┴───────────────────────────────────┐
   │ 设备返回版本信息              设备返回 "% Invalid"
   │      │                               │
   ▼      ▼                               ▼
detect_brand()                  发送 "show version"
返回 h3c 或 huawei                      │
        │                      detect_brand()
        └──────────────────────返回 cisco/ruijie/tplink
                    │
                    ▼
          保存 brand_detected
          提取 model_detected
```

---

## 五、型号提取：`_extract_model()`

### 5.1 什么是型号？

品牌之外，我们还想知道具体是哪款交换机，例如 `S5560-54C-EI`（H3C）或 `WS-C2960X-24TS-L`（Cisco）。

### 5.2 实现方式：正则表达式两步提取

```python
# core/ssh_manager_simple.py  第 246-269 行

def _extract_model(self, version_output: str, brand: str) -> str:
    """从 version 输出中提取设备型号"""

    # 每个品牌的版本输出格式不同，需要用不同的正则
    # 格式：(定位行的正则,  去掉多余内容的正则)
    patterns = {
        # H3C 格式：  "H3C S5560-54C-EI uptime is 10 weeks"
        #                  ^^^^^^^^^^^^^ 这里是型号
        'h3c':    (r'^h3c.*uptime',    r' *uptime.*$'),

        # 华为格式：  "Huawei S5735-L48P4X uptime is 3 days"
        'huawei': (r'^huawei.*uptime', r' *uptime.*$'),

        # 思科格式：  "cisco WS-C2960X-24TS-L (PowerPC405) processor"
        #                   ^^^^^^^^^^^^^^^^^ 这里是型号
        'cisco':  (r'^cisco.*processor', r' *\(.*$'),

        'ruijie': (r'^ruijie.*software', r' *software.*$'),
        'tplink': (r'^tp-link.*software', r' *software.*$'),
    }

    search_pat, sub_pat = patterns.get(brand, ('', ''))
    if not search_pat:
        return ''

    # 逐行扫描版本输出
    for line in version_output.split('\n'):
        line = line.strip()

        # 步骤1：用 search_pat 找到"包含型号信息"的那一行
        if re.search(search_pat, line, re.IGNORECASE):

            # 步骤2：用 sub_pat 删除 "uptime..." 之后的无用内容
            model = re.sub(sub_pat, '', line, flags=re.IGNORECASE)

            # 步骤3：删除开头的品牌名（只保留型号）
            # 例如 "H3C S5560-54C-EI" → "S5560-54C-EI"
            model = re.sub(
                r'^(cisco nexus|cisco|h3c|huawei|ruijie|tp-link)\s*',
                '',
                model,
                flags=re.IGNORECASE
            )
            return model.strip()

    return ''  # 没找到型号
```

### 5.3 正则表达式速查

| 符号 | 含义 | 例子 |
|------|------|------|
| `^` | 行开头 | `^h3c` 匹配以 "h3c" 开头的行 |
| `.*` | 任意字符（任意多个） | `h3c.*uptime` 匹配 "h3c ... uptime" |
| `\s*` | 任意空格（0个或多个） | `h3c\s*` 匹配 "h3c" 或 "h3c " |
| `$` | 行结尾 | `uptime.*$` 匹配 "uptime" 到行尾的所有内容 |
| `re.IGNORECASE` | 忽略大小写标志 | 让 `h3c` 也能匹配 `H3C` |

---

## 六、提示符识别正则：读取命令输出的基础

### 6.1 什么是提示符？

每次在交换机上执行完一条命令，设备会打印一个"提示符"，表示"我执行完了，等你下一条命令"：

```
<H3C>display version      ← "<H3C>" 就是提示符
... 版本输出内容 ...
<H3C>                     ← 命令执行完毕，再次出现提示符
```

工具需要检测到提示符，才知道命令输出已经结束，可以读取结果了。

### 6.2 核心正则（借鉴 w-sw-ssh）

```python
# core/ssh_manager_simple.py  第 37-39 行

PROMPT_REGEX = re.compile(
    r'(\r|\n).?[<>\[\]a-zA-Z0-9~@*/\\_\-\(\)]+(>|%|#|\$|\]) *$'
)
```

拆解解读：

```
(\r|\n)          → 必须有换行符（提示符出现在新行）
.?               → 可选的一个任意字符
[<>\[\]a-zA-Z0-9~@*/\\_\-\(\)]+
                 → 提示符主体：字母数字和各种符号（设备名）
(>|%|#|\$|\])    → 提示符结尾：> # ] $ % 之一
 *$              → 允许结尾有空格，然后到行末
```

各品牌提示符举例：

| 品牌 | 提示符样式 | 匹配位置 |
|------|-----------|---------|
| H3C | `<H3C>` | `>` 结尾 |
| H3C 系统视图 | `[H3C]` | `]` 结尾 |
| 华为 | `<Huawei>` | `>` 结尾 |
| Cisco | `Switch#` | `#` 结尾 |
| Cisco 特权前 | `Router>` | `>` 结尾 |
| 锐捷 | `ruijie#` | `#` 结尾 |

一个宽松的正则覆盖了所有品牌，省去了为每个品牌单独写检测逻辑。

---

## 七、命令翻译机制：`translate_command_for_brand()`

### 7.1 解决什么问题？

用户在 `SSH_command.txt` 里写了一份命令列表（H3C 格式）：
```
display interface brief
display vlan
display arp
```

如果要连接 Cisco 设备，这些命令全部无效。过去的做法是准备多份文件，
工具改进后，运行时自动翻译：

```
display interface brief  →  show ip interface brief  （Cisco）
display vlan             →  show vlan brief           （Cisco）
display arp              →  show arp                  （Cisco，碰巧相同）
```

### 7.2 翻译原理：构建反向查找表

```python
# config/device_commands.py  第 233-269 行

def translate_command_for_brand(command: str, brand: str) -> str:

    brand_cmds = get_device_commands(brand)   # 取目标品牌的命令字典

    # ── 第一步：建立"命令字符串 → 命令键"的反向映射 ──
    # 正向映射（原始数据）：命令键 → 命令字符串
    #   'display_interface': 'display interface brief'   (H3C)
    #   'display_interface': 'show ip interface brief'   (Cisco)
    #
    # 反向映射（我们构建的）：命令字符串 → 命令键
    #   'display interface brief' → 'display_interface'
    #   'show ip interface brief' → 'display_interface'

    cmd_to_key = {}
    for cmds in DEVICE_COMMANDS.values():        # 遍历所有品牌
        for key, cmd_str in cmds.items():
            if key.startswith('l2_') or key in ('nomore', 'save_config', 'logout'):
                continue                          # 运维命令不做翻译
            cmd_to_key[cmd_str.lower()] = key     # 命令字符串 → 键

    # ── 第二步：用输入命令查键，再用键查目标品牌命令 ──
    cmd_lower = command.strip().lower()
    key = cmd_to_key.get(cmd_lower)              # "display interface brief" → "display_interface"

    if key and key in brand_cmds:
        return brand_cmds[key]                   # "display_interface" → "show ip interface brief"

    return command                               # 没找到对应翻译，原样返回
```

### 7.3 翻译示意图

```
输入命令：  "display interface brief"
               │
               ▼
    反向查找表查找
    'display interface brief' → 键 = 'display_interface'
               │
               ▼
    在 Cisco 命令字典中查 'display_interface'
    结果 = 'show ip interface brief'
               │
               ▼
    实际发送给 Cisco 设备的命令：
    "show ip interface brief"
```

---

## 八、代码结构总览

```
Switch_SSH_Tools/
│
├── config/device_commands.py       ← 品牌配置层（纯数据，无网络操作）
│   ├── BRAND_KEYWORDS              数据：各品牌识别关键字
│   ├── DEVICE_COMMANDS             数据：各品牌完整命令字典
│   ├── detect_brand()              函数：文本 → 品牌字符串
│   ├── get_device_commands()       函数：品牌 → 命令字典
│   ├── get_command()               函数：品牌 + 键 → 具体命令
│   └── translate_command_for_brand() 函数：H3C命令 → 目标品牌命令
│
└── core/ssh_manager_simple.py      ← SSH 执行层（网络操作）
    ├── PROMPT_REGEX                常量：提示符识别正则
    ├── SSHConnection               类：单台设备的连接与操作
    │   ├── connect()               方法：建立SSH连接（6步流程）
    │   ├── _detect_brand_and_model() 方法：两步品牌识别
    │   ├── _extract_model()        方法：正则提取设备型号
    │   ├── _read_until_prompt()    方法：读取命令输出（检测提示符）
    │   ├── execute_command()       方法：执行单条命令
    │   └── execute_commands()      方法：批量执行（含品牌感知翻译）
    └── SSHManager                  类：多台设备的并发调度
        └── connect_all()           方法：ThreadPoolExecutor 并发连接
```

**各层职责说明：**

- `device_commands.py`：只负责"知识存储"——各品牌用什么命令、怎么识别品牌。
  修改品牌支持时只改这一个文件，其他代码不动。
- `ssh_manager_simple.py`：只负责"网络执行"——建连接、发命令、读结果。
  不关心具体命令是什么，从配置层获取。

这种"**配置与执行分离**"的设计，是本项目最核心的架构思想。

---

## 九、性能优化建议

### 9.1 已实现的优化：ThreadPoolExecutor

```python
# 原始方案（串行）：设备1 完成 → 设备2 开始 → ...
# 连接 20 台设备，每台 5 秒 → 总耗时 100 秒

# 现有方案（并发）：所有设备同时开始连接
# 连接 20 台设备，每台 5 秒，5 并发 → 总耗时约 20 秒
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(conn.connect): conn for conn in connections}
    for future in as_completed(futures):   # 哪个设备先完成先处理哪个
        result = future.result()
```

**关键改进**：`as_completed` 比 `futures.result()` 更好，
因为慢速设备不会阻塞快速设备的结果处理。

### 9.2 可进一步优化的方向

**方向 1：缓存已识别品牌**

```python
# 当前：每次连接都要执行两条版本命令（每条约 0.5-2 秒）
# 改进：记录每个 IP 上次识别的品牌，下次连接直接跳过识别

_brand_cache = {}   # { '192.168.1.1': 'h3c' }

def _detect_brand_and_model(self):
    ip = self.device_info.ip
    if ip in _brand_cache:
        self.brand_detected = _brand_cache[ip]   # 直接使用缓存
        return
    # ... 正常识别流程 ...
    _brand_cache[ip] = self.brand_detected       # 保存到缓存
```

**方向 2：批量构建翻译表（避免重复计算）**

```python
# 当前：每次调用 translate_command_for_brand() 都重建反向映射
# 改进：程序启动时构建一次，之后复用

# 在模块级别预构建（只执行一次）
_CMD_TO_KEY: dict = {}
for cmds in DEVICE_COMMANDS.values():
    for key, cmd_str in cmds.items():
        if not key.startswith('l2_') and key not in ('nomore', 'save_config', 'logout'):
            _CMD_TO_KEY[cmd_str.lower()] = key
```

**方向 3：增大并发数（谨慎）**

```python
# 当前：max_workers=5
# 可以增大，但要注意：
# - 太大会导致设备 SSH 服务拒绝连接（很多设备限制并发 SSH 会话数 ≤ 5）
# - 建议范围：5~15，根据实际网络情况调整

SSHManager(max_connections=10)
```

**方向 4：连接池复用**

```python
# 当前：每次任务都重新建立 SSH 连接（握手耗时约 0.5-1 秒）
# 改进：保持长连接，下次任务直接复用已建立的 SSH 会话
# 实现：在 SSHConnection 中添加 keepalive 心跳，连接对象不主动断开
```

---

## 十、新手总结：核心思路对比

| 概念 | 图像品牌识别（商标检测） | 本项目（交换机品牌识别） |
|------|------------------------|------------------------|
| 输入数据 | 图片（像素矩阵） | 命令行文本（字符串） |
| 特征提取 | 颜色直方图、边缘形状、CNN特征图 | 特定关键字（h3c、comware 等） |
| 识别模型 | 卷积神经网络（需要训练） | 有序优先级规则字典（专家知识编码） |
| 训练数据 | 需要大量标注图片 | 不需要训练，直接编写规则 |
| 准确率 | 依赖训练数据质量 | 依赖关键字覆盖的完整性 |
| 扩展方式 | 重新收集数据并训练 | 在字典中添加新品牌条目 |
| 适用场景 | 图像中的视觉特征识别 | 结构化协议文本中的标识符识别 |

**核心结论**：选择哪种识别方式，取决于数据的性质。
交换机的版本输出是**高度结构化、规则可预期**的文本，
使用"关键字字典 + 优先级匹配"比机器学习更简单、更快速、更可靠。

---

*本文档对应代码版本：v2.0.0（2026-03-18）*
