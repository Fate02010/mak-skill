# Terminal Model

## Supported Terminal Types

The skill supports these first-class terminal types:

- `admin` → `后台`
- `miniapp` → `小程序`
- `app` → `App`
- `h5` → `H5`
- `bigscreen` → `大屏`
- `portal` → `官网门户`
- `industrial` → `工控机`

## Naming Rule

`module_name` must use:

`[terminal_name]-[业务模块]`

Examples:

- `后台-订单管理`
- `小程序-首页`
- `App-会员中心`
- `H5-活动报名`
- `大屏-指挥中心`
- `官网门户-产品官网`
- `工控机-产线监控`

Reject generic system-only names such as:

- `后台管理`
- `APP系统`
- `官网门户`
- `大屏`
- `工控机界面`

## Terminal Semantics

- `admin`: web back-office, menu/tree/navigation semantics
- `miniapp`: mobile mini-program navigation semantics
- `app`: native app-like mobile semantics
- `h5`: mobile web page-stack semantics, not miniapp by default
- `portal`: public website or logged-in portal entry semantics
- `bigscreen`: 16:9 board / cockpit / command center semantics
- `industrial`: full-screen HMI / control console semantics
