# NSFW Guard Pro 🛡️

[English](#english) | [中文](#中文)

---

<a name="english"></a>
## English

NSFW Guard Pro is a pro-grade, **100% Local** AI solution for image content moderation. It leverages Vision Transformers (ViT) and NudeNet to provide precise classification and automated censoring without ever sending your data to the cloud.

### 🌟 Key Features
- **Smart Censoring**: Choose between **Gaussian Blur**, **Pixelation**, or **Solid Color** masks.
- **Deep Scan Mode**: 3x3 tiling strategy ensures even tiny sensitive areas in high-res images are captured.
- **Normal Confidence Override**: AI is now smart enough to avoid "false positives." If an image is 90% "Normal," it ignores ambiguous areas like belly or covered skin.
- **Multi-Platform Deployment**:
  - **Linux Server**: One-click install with `systemd` service support.
  - **Windows PC**: PowerShell installer with optional GPU/CUDA acceleration.
### 🚀 Quick Start

#### Linux (Ubuntu/Debian)
```bash
# Clone the repo and run the installer
chmod +x install_linux.sh
./install_linux.sh
```

#### Windows
1. Open PowerShell as Administrator.
2. Run: `.\install_windows.ps1`

---

<a name="中文"></a>
## 中文

NSFW Guard Pro 是一款专业级、**100% 本地化**的 AI 图像内容审核与自动打码方案。

### 🌟 核心亮点
- **智能打码**：提供 **高斯模糊**、**马赛克** 或 **纯色填充** 三种模式。
- **深度切片扫描 (Deep Scan)**：3x3 瓦片式扫描技术，不放过高分辨率图片中的任何微小敏感位置。
- **智能防误杀**：引入分类器优先逻辑。如果 AI 判断图片整体安全度 > 90%，将自动跳过露腹、紧身衣等模糊区域，杜绝误杀。
- **多平台快速部署**：
  - **Linux 服务器**：提供 `install_linux.sh` 脚本，支持硬件自动识别与 `systemd` 后台服务配置。
  - **Windows 家用电脑**：PowerShell 一键安装，支持调用 NVIDIA GPU (CUDA) 加速。

### 🚀 快速部署

#### Linux (Ubuntu/Debian)
```bash
# 赋予权限并执行安装脚本
chmod +x install_linux.sh
./install_linux.sh
```

#### Windows
1. 以管理员权限打开 PowerShell。
2. 执行: `.\install_windows.ps1`

---

## 📄 Documentation
- [Detailed API Docs](api_docs.md)
- [Implementation Walkthrough](walkthrough.md)

