# free-cf-temp-email

基于 Cloudflare 免费服务部署临时邮箱系统。

## 功能

- 临时邮箱地址创建、收发邮件
- Web 前端 + 管理后台
- 用户注册登录
- 支持 DigitalPlat 免费域名 (`*.dpdns.org`)

## 包含组件

| 组件 | 服务 | 费用 |
|------|------|------|
| Worker 后端 | Cloudflare Workers | 免费 |
| 数据库 | Cloudflare D1 | 免费 |
| 前端 | Cloudflare Pages | 免费 |
| 收件 | Email Routing | 免费 |
| 域名 | DigitalPlat | 免费 |

## 使用

输入 `/free-cf-temp-email` 调用此 skill，按指引操作即可。

完整流程：获取域名 → DNS 托管 → 登录 CF → 创建数据库 → 配置 Worker → 部署 → Email Routing → 部署前端 → 配置域名 → 开启注册

## 前置要求

- Node.js + npm
- Cloudflare 账号
- 域名（或通过 DigitalPlat 免费获取）

## 来源

项目：[cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email)
