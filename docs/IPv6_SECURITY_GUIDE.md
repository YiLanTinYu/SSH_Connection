# IPv6安全配置指南

## 概述

本文档提供SSH自动化运维工具在IPv6环境下的安全配置指南，包括防火墙规则、访问控制策略和安全最佳实践。

## IPv6安全基础

### IPv6与IPv4的主要安全差异

1. **地址空间**：IPv6拥有巨大的地址空间，传统的网络扫描攻击方式需要调整
2. **协议特性**：IPv6引入了新的协议头和扩展头，需要额外的安全考虑
3. **自动配置**：IPv6支持无状态地址自动配置(SLAAC)，需要适当的安全控制
4. **邻居发现**：NDP协议替代了ARP，需要相应的安全措施

## 防火墙配置

### 基本防火墙规则

#### 1. 允许已建立的连接

```bash
# 允许已建立的IPv6连接
ip6tables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
ip6tables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
```

#### 2. 允许SSH连接（指定端口）

```bash
# 允许SSH连接（默认端口22）
ip6tables -A INPUT -p tcp --dport 22 -m state --state NEW -j ACCEPT

# 如果使用自定义SSH端口，替换22为实际端口号
ip6tables -A INPUT -p tcp --dport 2222 -m state --state NEW -j ACCEPT
```

#### 3. 限制SSH连接频率

```bash
# 限制每分钟最多3个新SSH连接
ip6tables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set
ip6tables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 3 -j DROP
```

#### 4. 拒绝ICMPv6消息（选择性）

```bash
# 允许必要的ICMPv6消息
ip6tables -A INPUT -p icmpv6 --icmpv6-type destination-unreachable -j ACCEPT
ip6tables -A INPUT -p icmpv6 --icmpv6-type packet-too-big -j ACCEPT
ip6tables -A INPUT -p icmpv6 --icmpv6-type time-exceeded -j ACCEPT
ip6tables -A INPUT -p icmpv6 --icmpv6-type parameter-problem -j ACCEPT
ip6tables -A INPUT -p icmpv6 --icmpv6-type echo-request -j ACCEPT
ip6tables -A INPUT -p icmpv6 --icmpv6-type echo-reply -j ACCEPT

# 拒绝其他ICMPv6消息
ip6tables -A INPUT -p icmpv6 -j DROP
```

#### 5. 默认拒绝策略

```bash
# 设置默认拒绝策略
ip6tables -P INPUT DROP
ip6tables -P FORWARD DROP
ip6tables -P OUTPUT ACCEPT
```

### 高级防火墙规则

#### 1. 基于地址范围的访问控制

```bash
# 仅允许特定IPv6地址段访问SSH
ip6tables -A INPUT -p tcp --dport 22 -s 2001:db8::/32 -m state --state NEW -j ACCEPT

# 拒绝特定IPv6地址段
ip6tables -A INPUT -s 2001:db8:bad::/48 -j DROP
```

#### 2. 基于接口的访问控制

```bash
# 仅允许从特定接口访问SSH
ip6tables -A INPUT -i eth0 -p tcp --dport 22 -m state --state NEW -j ACCEPT

# 拒绝从特定接口的SSH连接
ip6tables -A INPUT -i eth1 -p tcp --dport 22 -j DROP
```

#### 3. 限制并发连接数

```bash
# 限制每个IPv6地址最多5个并发SSH连接
ip6tables -A INPUT -p tcp --dport 22 -m connlimit --connlimit-above 5 -j DROP
```

### 使用nftables（推荐）

nftables是现代Linux系统的防火墙工具，功能更强大：

```bash
# 创建nftables表
nft add table ip6 filter

# 创建链
nft add chain ip6 filter input { type filter hook input priority 0 \; }
nft add chain ip6 filter output { type filter hook output priority 0 \; }

# 允许已建立的连接
nft add rule ip6 filter input ct state established,related accept

# 允许SSH
nft add rule ip6 filter input tcp dport 22 ct state new accept

# 限制SSH连接频率
nft add rule ip6 filter input tcp dport 22 ct state new limit rate 3/minute accept

# 默认拒绝
nft add rule ip6 filter input drop
```

## SSH服务安全配置

### 1. 修改SSH默认端口

```bash
# 编辑SSH配置文件
sudo vi /etc/ssh/sshd_config

# 修改端口
Port 2222

# 重启SSH服务
sudo systemctl restart sshd
```

### 2. 禁用密码认证，使用密钥认证

```bash
# 编辑SSH配置文件
sudo vi /etc/ssh/sshd_config

# 禁用密码认证
PasswordAuthentication no
PubkeyAuthentication yes

# 重启SSH服务
sudo systemctl restart sshd
```

### 3. 限制登录用户

```bash
# 编辑SSH配置文件
sudo vi /etc/ssh/sshd_config

# 仅允许特定用户登录
AllowUsers admin@2001:db8::1 user2@2001:db8::2

# 或拒绝特定用户
DenyUsers root

# 重启SSH服务
sudo systemctl restart sshd
```

### 4. 配置IPv6监听地址

```bash
# 编辑SSH配置文件
sudo vi /etc/ssh/sshd_config

# 监听所有IPv6地址
ListenAddress ::

# 或监听特定IPv6地址
ListenAddress 2001:db8::1

# 重启SSH服务
sudo systemctl restart sshd
```

### 5. 启用失败登录尝试限制

```bash
# 使用fail2ban保护SSH
sudo apt-get install fail2ban

# 配置fail2ban
sudo vi /etc/fail2ban/jail.local

[sshd]
enabled = true
port = ssh,2222
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

# 启动fail2ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

## 网络设备安全配置

### H3C交换机IPv6安全配置

```bash
# 启用IPv6
ipv6

# 配置SSHv2
ssh server enable

# 配置SSH IPv6访问控制
acl ipv6 number 2000
rule permit source 2001:db8::/32

# 应用ACL到SSH
ssh server ipv6 acl 2000

# 限制SSH连接数
ssh server max-sessions 5

# 配置登录失败处理
login attempt max-times 3
login lockout-time 60
```

### Huawei交换机IPv6安全配置

```bash
# 启用IPv6
ipv6

# 启用SSH
stelnet server enable

# 配置IPv6 ACL
acl ipv6 number 2000
rule 5 permit tcp source 2001:db8::/32 destination-port eq 22

# 应用ACL到VTY
user-interface vty 0 4
acl ipv6 2000 inbound
protocol inbound ssh

# 配置登录限制
login attempt max-times 3
login lockout-time 60
```

### Cisco交换机IPv6安全配置

```bash
# 启用IPv6
ipv6 unicast-routing

# 配置SSH
ip ssh version 2

# 配置IPv6访问列表
ipv6 access-list SSH-ALLOW
permit tcp 2001:db8::/32 any eq 22
deny tcp any any eq 22

# 应用到VTY
line vty 0 4
access-class SSH-ALLOW in
transport input ssh

# 配置登录失败处理
login block-for 60 attempts 3 within 60
```

## 监控和日志

### 1. 启用IPv6连接日志

```bash
# 记录所有IPv6连接尝试
ip6tables -A INPUT -j LOG --log-prefix "IPv6-INPUT: "
ip6tables -A OUTPUT -j LOG --log-prefix "IPv6-OUTPUT: "

# 查看日志
tail -f /var/log/syslog | grep IPv6
```

### 2. 监控SSH连接

```bash
# 实时监控SSH连接
watch -n 1 'ss -t6 state established | grep :22'

# 查看IPv6连接统计
ss -s6
```

### 3. 配置日志轮转

```bash
# 创建日志轮转配置
sudo vi /etc/logrotate.d/ipv6-ssh

/var/log/ipv6-ssh.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root adm
}
```

## 安全最佳实践

### 1. 定期更新系统

```bash
# 更新系统软件包
sudo apt-get update
sudo apt-get upgrade

# 更新SSH服务
sudo apt-get install openssh-server
```

### 2. 使用强密码和密钥

```bash
# 生成SSH密钥对
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# 复制公钥到目标设备
ssh-copy-id -6 user@2001:db8::1
```

### 3. 定期审计安全配置

```bash
# 检查防火墙规则
sudo ip6tables -L -n -v

# 检查SSH配置
sudo sshd -T | grep -i "port\|listenaddress\|passwordauthentication"

# 检查开放端口
sudo ss -t6ulnp
```

### 4. 备份配置

```bash
# 备份防火墙规则
sudo ip6tables-save > /root/ipv6-firewall-backup.txt

# 备份SSH配置
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# 备份网络设备配置
# 根据不同品牌使用相应的备份命令
```

## 故障排除

### 常见问题

1. **IPv6连接失败**
   - 检查防火墙规则：`sudo ip6tables -L -n -v`
   - 检查SSH服务状态：`sudo systemctl status sshd`
   - 检查网络连通性：`ping6 2001:db8::1`

2. **防火墙规则不生效**
   - 确认规则顺序：`sudo ip6tables -L -n -v --line-numbers`
   - 检查默认策略：`sudo ip6tables -P`
   - 重新加载规则：`sudo ip6tables-restore < /root/ipv6-firewall-backup.txt`

3. **SSH连接被拒绝**
   - 检查SSH配置：`sudo sshd -T | grep -i listenaddress`
   - 检查监听地址：`sudo ss -t6lnp | grep sshd`
   - 查看SSH日志：`sudo tail -f /var/log/auth.log`

## 参考资源

- [IPv6安全最佳实践](https://www.rfc-editor.org/rfc/rfc4941)
- [SSH安全配置指南](https://www.ssh.com/academy/ssh/config)
- [nftables官方文档](https://wiki.nftables.org/)
- [fail2ban配置指南](https://fail2ban.readthedocs.io/)

## 版本历史

- v1.0 (2026-03-16): 初始版本，包含基本IPv6安全配置指南