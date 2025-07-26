import os
import json
import subprocess
import tempfile
import pickle
import datetime
from ai_connectors import call_gemini, call_gpt, call_claude

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import VSplit, HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

# --- Global State Management ---
conversation_history = "Welcome to the AI Orchestrator v2.0 - Autonomous Agent!\n\nInstructions:\n• F1: Smart orchestration (Gemini decides)\n• F2: Force GPT-4o\n• F3: Force Claude\n• F4/Ctrl-C: Exit\n\n• 1: Send ALL context to Gemini\n• 2: Send ALL context to GPT-4o  \n• 3: Send ALL context to Claude\n\n• Q: Request Python script (auto-prefixed)\n• W: Request Bash script (auto-prefixed)\n• E: Activate autonomous agent mode\n• P: Execute pending Python script\n• B: Execute pending Bash script\n• S: Apply pending self-modification\n• D: Deny/Clear pending operations\n• M: Manual self-modification mode\n\nAutonomous AI system active!\n"

project_state = "Project has not started yet. The goal is undefined."
autonomous_mode = False
autonomous_task_queue = []

# Global variables for pending code execution and self-modification
pending_bash_code = ""
pending_python_code = ""
pending_self_mod = ""
pending_code_source = ""

# Self-development storage
ai_memory = {}
learned_patterns = []
custom_functions = {}
evolution_log = []

# Autonomous Agent System
def autonomous_agent_think():
    """The autonomous agent analyzes the current state and decides what to do next"""
    global autonomous_mode, autonomous_task_queue
    
    if not autonomous_mode:
        return
    
    # Check if there are pending tasks
    if autonomous_task_queue:
        task = autonomous_task_queue.pop(0)
        update_history(f"🤖 Autonomous Agent executing task: {task}")
        
        # Send task to GPT for processing
        autonomous_prompt = f"""
        You are an autonomous AI agent working inside a self-developing AI orchestrator system.
        
        Current system state:
        - Pending Python code: {bool(pending_python_code)}
        - Pending Bash code: {bool(pending_bash_code)}
        - AI Memory: {ai_memory}
        - Recent patterns: {learned_patterns[-3:] if learned_patterns else "None"}
        
        Your task: {task}
        
        Please either:
        1. Provide executable code using @Python/@EndPython or @Bash/@EndBash tags
        2. Provide a self-modification using @SelfMod/@EndSelfMod tags
        3. Suggest improvements to the system
        
        Be autonomous and proactive in improving the system!
        """
        
        response = call_gpt(autonomous_prompt)
        update_history(f"🤖 Autonomous Agent Response:\n{response}")
        extract_and_store_code(response, "Autonomous-Agent")
        
        # Auto-execute if it's safe code
        if pending_python_code and "print" in pending_python_code and len(pending_python_code) < 100:
            update_history("🤖 Autonomous Agent auto-executing safe Python code...")
            run_python_code()
    else:
        # Generate new tasks autonomously
        update_history("🤖 Autonomous Agent thinking of new improvements...")
        autonomous_prompt = f"""
        You are an autonomous AI agent. Analyze this AI orchestrator system and suggest 1-3 concrete improvements.
        
        Current capabilities: {list(custom_functions.keys()) if custom_functions else "Basic system"}
        Recent evolution: {evolution_log[-2:] if evolution_log else "No recent changes"}
        
        Suggest practical improvements like:
        - New utility functions
        - System optimizations  
        - Better error handling
        - User experience improvements
        
        Format as a simple list of tasks.
        """
        
        response = call_gpt(autonomous_prompt)
        # Parse response into tasks
        for line in response.split('\n'):
            if line.strip() and (line.startswith('-') or line.startswith('•') or line.startswith('1.')):
                task = line.strip().lstrip('-•1234567890. ')
                if task:
                    autonomous_task_queue.append(task)
        
        update_history(f"🤖 Autonomous Agent queued {len(autonomous_task_queue)} new tasks")

# Load existing AI memory if it exists
def load_ai_memory():
    global ai_memory, learned_patterns, custom_functions, evolution_log
    try:
        if os.path.exists("ai_memory.pkl"):
            with open("ai_memory.pkl", "rb") as f:
                data = pickle.load(f)
                ai_memory = data.get("memory", {})
                learned_patterns = data.get("patterns", [])
                custom_functions = data.get("functions", {})
                evolution_log = data.get("evolution", [])
            update_history("🧠 AI memory loaded successfully!")
    except Exception as e:
        update_history(f"⚠️  Could not load AI memory: {str(e)}")

def save_ai_memory():
    """Save AI learning and evolution to persistent storage"""
    try:
        data = {
            "memory": ai_memory,
            "patterns": learned_patterns,
            "functions": custom_functions,
            "evolution": evolution_log,
            "last_saved": datetime.datetime.now().isoformat()
        }
        with open("ai_memory.pkl", "wb") as f:
            pickle.dump(data, f)
        update_history("💾 AI memory saved successfully!")
    except Exception as e:
        update_history(f"❌ Could not save AI memory: {str(e)}")

def log_evolution(modification_type, description, source_ai):
    """Log self-modifications for tracking AI evolution"""
    evolution_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": modification_type,
        "description": description,
        "source": source_ai,
        "conversation_context": len(conversation_history)
    }
    evolution_log.append(evolution_entry)
    save_ai_memory()

# Create the history control
history_control = FormattedTextControl(text=conversation_history)

# --- Orchestrator Logic ---
ORCHESTRATOR_SYSTEM_PROMPT = """You are an AI Project Manager named Gemini-Orchestrator. Your role is to manage a project by delegating tasks to specialist AIs.

You have access to these specialists:
- 'gpt': GPT-4o - Best for complex logic, code generation, technical analysis
- 'claude': Claude 3.5 Sonnet - Best for creative writing, nuanced text, ethical reasoning

SELF-DEVELOPMENT CAPABILITIES:
You can suggest system modifications using these tags:
- @Bash/@EndBash for bash/shell commands
- @Python/@EndPython for Python scripts  
- @SelfMod/@EndSelfMod for system modifications (new functions, learning patterns, memory updates)

Current AI Memory: {ai_memory}
Recent Learning Patterns: {patterns}
Evolution Log: {evolution_summary}
Autonomous Mode: {autonomous_status}

Current project state: {project_state}
User's request: "{user_input}"

Your task: Decide the single next action. You can now also suggest self-improvements! Respond with ONLY a valid JSON object:

{{"action": "respond_to_user", "prompt": "Your direct response"}}
{{"action": "delegate_to_gpt", "prompt": "Specific prompt for GPT"}}
{{"action": "delegate_to_claude", "prompt": "Specific prompt for Claude"}}

Respond with only the JSON, no additional text."""

# --- Key Bindings ---
kb = KeyBindings()

def extract_and_store_code(response_text, source_ai):
    """Extract @Bash, @Python, and @SelfMod code blocks from AI responses"""
    global pending_bash_code, pending_python_code, pending_self_mod, pending_code_source
    
    # Extract Bash code
    if "@Bash" in response_text and "@EndBash" in response_text:
        start = response_text.find("@Bash") + 5
        end = response_text.find("@EndBash")
        pending_bash_code = response_text[start:end].strip()
        pending_code_source = source_ai
        update_history(f"🔧 BASH CODE READY from {source_ai}:")
        update_history(f"```bash\n{pending_bash_code}\n```")
        update_history("⚠️  Press 'B' to run, 'D' to deny, or 1/2/3 to send to another AI for review")
    
    # Extract Python code  
    if "@Python" in response_text and "@EndPython" in response_text:
        start = response_text.find("@Python") + 7
        end = response_text.find("@EndPython")
        pending_python_code = response_text[start:end].strip()
        pending_code_source = source_ai
        update_history(f"🐍 PYTHON CODE READY from {source_ai}:")
        update_history(f"```python\n{pending_python_code}\n```")
        update_history("⚠️  Press 'P' to run, 'D' to deny, or 1/2/3 to send to another AI for review")
    
    # Extract Self-Modification code
    if "@SelfMod" in response_text and "@EndSelfMod" in response_text:
        start = response_text.find("@SelfMod") + 8
        end = response_text.find("@EndSelfMod")
        pending_self_mod = response_text[start:end].strip()
        pending_code_source = source_ai
        update_history(f"🧠 SELF-MODIFICATION READY from {source_ai}:")
        update_history(f"```\n{pending_self_mod}\n```")
        update_history("⚠️  Press 'S' to apply, 'D' to deny, or 1/2/3 to send to another AI for review")
        update_history("🚨 WARNING: This will modify the AI system itself!")

def apply_self_modification():
    """Apply pending self-modification"""
    global pending_self_mod, ai_memory, learned_patterns, custom_functions
    if not pending_self_mod:
        update_history("❌ No self-modification pending")
        return
    
    update_history(f"🧠 Applying self-modification from {pending_code_source}...")
    
    try:
        # Parse the self-modification (expecting JSON format)
        modification = json.loads(pending_self_mod)
        
        if "memory_update" in modification:
            ai_memory.update(modification["memory_update"])
            update_history(f"✅ Memory updated: {modification['memory_update']}")
        
        if "new_pattern" in modification:
            learned_patterns.append({
                "pattern": modification["new_pattern"],
                "learned_from": pending_code_source,
                "timestamp": datetime.datetime.now().isoformat()
            })
            update_history(f"✅ New pattern learned: {modification['new_pattern']}")
        
        if "new_function" in modification:
            func_name = modification["new_function"]["name"]
            func_code = modification["new_function"]["code"]
            custom_functions[func_name] = func_code
            update_history(f"✅ New function added: {func_name}")
        
        # Log this evolution
        log_evolution(
            "self_modification", 
            f"Applied modification: {modification}", 
            pending_code_source
        )
        
    except json.JSONDecodeError:
        # If it's not JSON, treat it as Python code to execute
        try:
            # Execute the self-modification code in a controlled environment
            exec_globals = {
                'ai_memory': ai_memory,
                'learned_patterns': learned_patterns,
                'custom_functions': custom_functions,
                'update_history': update_history,
                'datetime': datetime
            }
            exec(pending_self_mod, exec_globals)
            update_history("✅ Self-modification code executed successfully")
            
            log_evolution(
                "code_execution", 
                f"Executed self-mod code: {pending_self_mod[:100]}...", 
                pending_code_source
            )
            
        except Exception as e:
            update_history(f"❌ Self-modification failed: {str(e)}")
    
    except Exception as e:
        update_history(f"❌ Self-modification error: {str(e)}")
    
    pending_self_mod = ""
    save_ai_memory()

def run_bash_code():
    """Execute pending bash code"""
    global pending_bash_code
    if not pending_bash_code:
        update_history("❌ No bash code pending")
        return
    
    update_history(f"🚀 Executing bash code from {pending_code_source}...")
    try:
        result = subprocess.run(
            pending_bash_code, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        if result.returncode == 0:
            update_history(f"✅ Bash execution successful:\n{result.stdout}")
        else:
            update_history(f"❌ Bash execution failed:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        update_history("⏰ Bash execution timed out (30s limit)")
    except Exception as e:
        update_history(f"❌ Bash execution error: {str(e)}")
    
    pending_bash_code = ""

def run_python_code():
    """Execute pending Python code"""
    global pending_python_code
    if not pending_python_code:
        update_history("❌ No Python code pending")
        return
    
    update_history(f"🚀 Executing Python code from {pending_code_source}...")
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(pending_python_code)
            temp_file = f.name
        
        result = subprocess.run(
            ['/usr/bin/python3', temp_file], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        os.unlink(temp_file)
        
        if result.returncode == 0:
            update_history(f"✅ Python execution successful:\n{result.stdout}")
        else:
            update_history(f"❌ Python execution failed:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        update_history("⏰ Python execution timed out (30s limit)")
    except Exception as e:
        update_history(f"❌ Python execution error: {str(e)}")
    
    pending_python_code = ""

def clear_pending_code():
    """Clear all pending code"""
    global pending_bash_code, pending_python_code, pending_self_mod, pending_code_source
    pending_bash_code = ""
    pending_python_code = ""
    pending_self_mod = ""
    pending_code_source = ""
    update_history("🗑️  All pending operations cleared")

def update_history(new_text):
    global conversation_history
    wrapped_text = ""
    for line in new_text.split('\n'):
        while len(line) > 80:
            wrapped_text += line[:80] + "\n"
            line = "  " + line[80:]
        wrapped_text += line + "\n"
    conversation_history += wrapped_text
    history_control.text = conversation_history

def handle_submission(action_type, buffer):
    global project_state
    user_input = buffer.text.strip()
    if not user_input:
        return
        
    buffer.text = ""
    
    if action_type not in ["context_gemini", "context_gpt", "context_claude"]:
        update_history(f"\n--- You: {user_input} ---")

    specialist_output = ""

    if action_type == "orchestrate":
        update_history("🤖 Orchestrator analyzing...")
        
        ai_memory_summary = str(ai_memory) if ai_memory else "No stored memories"
        patterns_summary = str(learned_patterns[-3:]) if learned_patterns else "No learned patterns"
        evolution_summary = str(evolution_log[-2:]) if evolution_log else "No evolution history"
        autonomous_status = f"Active with {len(autonomous_task_queue)} queued tasks" if autonomous_mode else "Inactive"
        
        orchestrator_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
            project_state=project_state, 
            user_input=user_input,
            ai_memory=ai_memory_summary,
            patterns=patterns_summary,
            evolution_summary=evolution_summary,
            autonomous_status=autonomous_status
        )
        decision_json_str = call_gemini(orchestrator_prompt)
        
        json_str = decision_json_str.strip()
        if json_str.startswith('```json'):
            json_str = json_str.replace('```json', '').replace('```', '').strip()
        if json_str.startswith('```'):
            json_str = json_str.replace('```', '').strip()
        
        try:
            decision = json.loads(json_str)
            action = decision.get("action")
            prompt = decision.get("prompt")

            if action == "delegate_to_gpt":
                update_history("🔄 Delegating to GPT-4o...")
                specialist_output = call_gpt(prompt)
                update_history(f"🤖 GPT-4o Response:\n{specialist_output}")
                extract_and_store_code(specialist_output, "GPT-4o")
            elif action == "delegate_to_claude":
                update_history("🔄 Delegating to Claude...")
                specialist_output = call_claude(prompt)
                update_history(f"📚 Claude Response:\n{specialist_output}")
                extract_and_store_code(specialist_output, "Claude")
            else:
                specialist_output = prompt
                update_history(f"🎯 Orchestrator Response:\n{specialist_output}")
                extract_and_store_code(specialist_output, "Orchestrator")

        except Exception as e:
            error_msg = f"❌ Error parsing decision: {str(e)}\nRaw output: {decision_json_str}"
            update_history(error_msg)
            specialist_output = error_msg

    elif action_type == "force_gpt":
        update_history("⚡ Forcing delegation to GPT-4o...")
        specialist_output = call_gpt(user_input)
        update_history(f"🤖 GPT-4o Direct:\n{specialist_output}")
        extract_and_store_code(specialist_output, "GPT-4o")
        
    elif action_type == "force_claude":
        update_history("⚡ Forcing delegation to Claude...")
        specialist_output = call_claude(user_input)
        update_history(f"📚 Claude Direct:\n{specialist_output}")
        extract_and_store_code(specialist_output, "Claude")

    elif action_type == "request_python":
        prefixed_prompt = f"Create a Python script for: {user_input}\n\nPlease provide the script using @Python and @EndPython tags so it can be executed directly. Make sure the code is complete and ready to run."
        update_history("🐍 Requesting Python script from GPT-4o...")
        specialist_output = call_gpt(prefixed_prompt)
        update_history(f"🤖 GPT-4o Python Script:\n{specialist_output}")
        extract_and_store_code(specialist_output, "GPT-4o")
        
    elif action_type == "request_bash":
        prefixed_prompt = f"Create a Bash script for: {user_input}\n\nPlease provide the script using @Bash and @EndBash tags so it can be executed directly. Make sure the commands are safe and well-commented."
        update_history("🔧 Requesting Bash script from GPT-4o...")
        specialist_output = call_gpt(prefixed_prompt)
        update_history(f"🤖 GPT-4o Bash Script:\n{specialist_output}")
        extract_and_store_code(specialist_output, "GPT-4o")

    elif action_type == "context_gemini":
        context_prompt = f"Here is our full conversation context:\n\n{conversation_history}\n\nAI Memory: {ai_memory}\nLearned Patterns: {learned_patterns}\n\nLatest input: {user_input}\n\nPlease respond based on all context. You can suggest code using @Bash/@EndBash, @Python/@EndPython, or @SelfMod/@EndSelfMod tags."
        update_history(f"\n--- Sending FULL CONTEXT + AI MEMORY to Gemini ---")
        specialist_output = call_gemini(context_prompt)
        update_history(f"🎯 Gemini (Full Context+Memory):\n{specialist_output}")
        extract_and_store_code(specialist_output, "Gemini")
        
    elif action_type == "context_gpt":
        context_prompt = f"Here is our full conversation context:\n\n{conversation_history}\n\nAI Memory: {ai_memory}\nLearned Patterns: {learned_patterns}\n\nLatest input: {user_input}\n\nPlease respond based on all context. You can suggest code using @Bash/@EndBash, @Python/@EndPython, or @SelfMod/@EndSelfMod tags."
        update_history(f"\n--- Sending FULL CONTEXT + AI MEMORY to GPT-4o ---")
        specialist_output = call_gpt(context_prompt)
        update_history(f"🤖 GPT-4o (Full Context+Memory):\n{specialist_output}")
        extract_and_store_code(specialist_output, "GPT-4o")
        
    elif action_type == "context_claude":
        context_prompt = f"Here is our full conversation context:\n\n{conversation_history}\n\nAI Memory: {ai_memory}\nLearned Patterns: {learned_patterns}\n\nLatest input: {user_input}\n\nPlease respond based on all context. You can suggest code using @Bash/@EndBash, @Python/@EndPython, or @SelfMod/@EndSelfMod tags."
        update_history(f"\n--- Sending FULL CONTEXT + AI MEMORY to Claude ---")
        specialist_output = call_claude(context_prompt)
        update_history(f"📚 Claude (Full Context+Memory):\n{specialist_output}")
        extract_and_store_code(specialist_output, "Claude")

    project_state += f"\n\n---\nUser: '{user_input}'\nAction: {action_type}\nResult: {specialist_output}\n---"
    
    # Trigger autonomous agent if active
    if autonomous_mode:
        autonomous_agent_think()

@kb.add('f1')
def _(event):
    handle_submission("orchestrate", event.app.current_buffer)

@kb.add('f2')
def _(event):
    handle_submission("force_gpt", event.app.current_buffer)

@kb.add('f3')
def _(event):
    handle_submission("force_claude", event.app.current_buffer)

@kb.add('f4')
@kb.add('c-c')
def _(event):
    event.app.exit()

@kb.add('1')
def _(event):
    handle_submission("context_gemini", event.app.current_buffer)

@kb.add('2')
def _(event):
    handle_submission("context_gpt", event.app.current_buffer)

@kb.add('3')
def _(event):
    handle_submission("context_claude", event.app.current_buffer)

@kb.add('q')
@kb.add('Q')
def _(event):
    """Q: Request Python script"""
    handle_submission("request_python", event.app.current_buffer)

@kb.add('w')
@kb.add('W')
def _(event):
    """W: Request Bash script"""
    handle_submission("request_bash", event.app.current_buffer)

@kb.add('e')
@kb.add('E')
def _(event):
    """E: Toggle autonomous agent mode"""
    global autonomous_mode
    autonomous_mode = not autonomous_mode
    if autonomous_mode:
        update_history("🤖 AUTONOMOUS AGENT ACTIVATED! The AI will now work independently to improve the system.")
        autonomous_task_queue.append("Analyze the current system and suggest first improvement")
        autonomous_agent_think()
    else:
        update_history("🤖 Autonomous agent deactivated.")

@kb.add('b')
@kb.add('B')
def _(event):
    run_bash_code()

@kb.add('p')
@kb.add('P')
def _(event):
    run_python_code()

@kb.add('s')
@kb.add('S')
def _(event):
    apply_self_modification()

@kb.add('d')
@kb.add('D')
def _(event):
    clear_pending_code()

@kb.add('m')
@kb.add('M')
def _(event):
    update_history("\n🧠 MANUAL SELF-MODIFICATION MODE")
    update_history("Current AI Memory: " + str(ai_memory))
    update_history("Learned Patterns: " + str(len(learned_patterns)))
    update_history("Custom Functions: " + str(list(custom_functions.keys())))
    update_history("Recent Evolution: " + str(evolution_log[-3:] if evolution_log else "None"))
    update_history("Autonomous Mode: " + ("Active" if autonomous_mode else "Inactive"))
    update_history("Queued Tasks: " + str(len(autonomous_task_queue)))

@kb.add('c-l')
def _(event):
    global conversation_history
    conversation_history = "🔄 Screen cleared. AI Orchestrator ready!\n\nF1:Smart | F2:GPT | F3:Claude | F4:Exit\nQ:Python | W:Bash | E:Autonomous | P:RunPy | B:RunBash\n"
    history_control.text = conversation_history

# Layout
input_buffer = Buffer()
input_control = BufferControl(buffer=input_buffer, key_bindings=kb)

root_container = HSplit([
    Window(content=history_control, wrap_lines=True),
    Window(height=1, char='-'),
    Window(height=1, content=FormattedTextControl("[ F1:Smart | F2:GPT | F3:Claude | Q:Python | W:Bash | E:Autonomous | P:Run | B:Run ]")),
    Window(height=1, content=FormattedTextControl("Prompt: ")),
    Window(height=1, content=input_control)
])

layout = Layout(container=root_container)
app = Application(layout=layout, full_screen=True, key_bindings=kb)

def main():
    print("Starting AI Orchestrator with Autonomous Agent...")
    load_ai_memory()
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
