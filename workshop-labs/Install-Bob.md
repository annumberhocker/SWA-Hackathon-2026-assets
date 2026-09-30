# Lab: Installing and Setting Up IBM Bob

**Hackathon Track: Tooling & Environment Setup**

In this lab, you will download, install, and configure **IBM Bob** (IDE and CLI/Shell) on your machine and verify your environment is ready for the workshop labs.

---

## Part 1 — Request Access & Download IBM Bob

### Step 1.1 — Access & Sign In
1. Visit [https://bob.ibm.com/trial](https://bob.ibm.com/trial) to start your free trial.
2. Sign up or sign in with your IBM account (or create one if you don't have one yet).
3. Once signed in, proceed to the [IBM Bob Download Page](https://bob.ibm.com/download).

### Step 1.2 — Download and Install IBM Bob IDE

Choose the installer matching your operating system and CPU architecture:

#### **macOS**
Check your chip type: Click ** (Apple menu) → About This Mac** → check **Chip / Processor**.
- **Apple Silicon (M1/M2/M3/M4):** Download the **mac-ARM** installer (`.pkg` or `.dmg`).
- **Intel Mac:** Download the **mac-intel** installer (`.pkg` or `.dmg`).

*Installation:*
- If using `.pkg` (recommended): Open the package and follow the installation wizard.
- If using `.dmg`: Open the `.dmg` and drag the **IBM Bob** application icon into your `/Applications` folder.

#### **Windows**
1. Download the `.exe` installer for Windows.
2. Run the downloaded installer.
3. Follow the wizard prompts and keep the default installation path.
4. Click **Finish**.

#### **Linux**
- **Ubuntu / Debian (`.deb`):**
  ```bash
  sudo apt install ./IBM-Bob-linux-amd64-<version>.deb
  ```
- **Red Hat / Fedora (`.rpm`):**
  ```bash
  sudo dnf install ./IBM-Bob-linux-x64-<version>.rpm
  ```

---

## Part 2 — Launch and Authenticate IBM Bob

1. Launch **IBM Bob** from your Applications (macOS), Start Menu (Windows), or launcher (Linux).
2. On first launch, click **Sign In** when prompted.
3. Complete the authentication flow in your default browser using your IBM account credentials.
4. Return to IBM Bob once browser confirmation appears.

---

## Part 3 — Install Bob Shell (CLI) *(Optional but Recommended)*

Bob Shell provides CLI integration and terminal workflows.

Open a terminal and run the installation script for your OS:

#### **macOS / Linux:**
```bash
curl -fsSL https://bob.ibm.com/download/bobshell.sh | bash
```

#### **Windows (PowerShell):**
```powershell
powershell -ep Bypass 'irm -Uri "https://bob.ibm.com/download/bobshell.ps1" | iex'
```

Alternatively, from inside IBM Bob IDE:
1. Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux) to open the Command Palette.
2. Type `Install Bob Shell` or `run bobshell` and follow the prompt.

---

## Part 4 — Verify Bob and MCP Settings

### Step 4.1 — Verify Bob Chat & Model Access
1. In the Bob IDE sidebar, click the **Chat** icon.
2. Type a greeting or simple prompt (e.g. `Hello Bob, are you ready for the hackathon?`).
3. Confirm Bob replies in the chat panel.

### Step 4.2 — Open MCP Server Settings
1. Click the **Gear icon** (Settings) in the top-right corner of the Bob interface.
2. Select **MCP Servers**.
3. Notice the MCP server list interface. In the upcoming labs:
   - In **Lab 1**, you will configure the `confluent` MCP server.
   - In **Lab 2**, you will configure the `watsonx-orchestrate-adk` MCP server.

---

## Next Steps

Now that IBM Bob is installed and authenticated, proceed to the workshop labs:

1. [Lab 1: Bob + Confluent — Real-Time Flight Anomaly Detection](Bob-and-Confluent.md)
2. [Lab 2: Bob + watsonx Orchestrate — Flight Triage Agent & Knowledge Base Setup](Bob-and-WXO.md)
