import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_sleek_solver_architecture_flowchart():
    """Generates a high-quality, sleek flow chart based on the user's sketch."""
    
    # Set up the figure and axis
    fig, ax = plt.subplots(figsize=(14, 12))
    ax.set_xlim(1.5, 12.5)
    ax.set_ylim(0.5, 10.5)
    ax.axis('off')

    # Define colors and styles - Professional Tech Color Scheme
    COLOR_INPUT = '#0066CC'        # Professional Blue
    COLOR_CORE = '#004B87'         # Deep Blue
    COLOR_HEURISTICS = '#2D5AA6'   # Medium Blue
    COLOR_BASELINE = '#1E3A5F'     # Dark Blue
    COLOR_RL_AGENT = '#6B4CE6'     # Purple
    COLOR_BANDIT = '#8B5CF6'       # Light Purple
    COLOR_RESULT = '#059669'       # Professional Green
    
    LINE_CORE = '#1F2937'          # Dark Gray
    LINE_BASELINE = '#374151'      # Medium Gray
    LINE_RL = '#6B21A8'            # Dark Purple

    # Define box dimensions
    w, h = 2.5, 0.7
    core_w, core_h = 3.5, 1.0 
    
    # --- 1. INPUT CNF (Top) ---
    input_x, input_y = 7, 10
    ax.add_patch(patches.Rectangle((input_x - w/2, input_y - h/2), w, h, facecolor=COLOR_INPUT, edgecolor=LINE_CORE, linewidth=2.5, alpha=1.0))
    plt.text(input_x, input_y, 'Input CNF', ha='center', va='center', fontsize=12, color='white', weight='bold')

    # --- 2. CORE CDCL ENGINE (Shared) ---
    core_x, core_y = 7, input_y - h - 1.0
    ax.add_patch(patches.Rectangle((core_x - core_w/2, core_y - core_h/2), core_w, core_h, facecolor=COLOR_CORE, edgecolor=LINE_CORE, linewidth=3, alpha=1.0))
    plt.text(core_x, core_y, 
             'Core CDCL Engine\n(used by both modes for \n accurate/fair comparision)',
             ha='center', va='center', fontsize=10, color='white', weight='bold')
    
    # Connect Input -> Core
    ax.annotate('', xy=(core_x, core_y + core_h/2), xytext=(input_x, input_y - h/2),
                arrowprops=dict(arrowstyle="->", color=LINE_CORE, lw=2.5))

    # --- Horizontal Split Line and Decision Point ---
    split_y = core_y - core_h/2 - 0.5
    
    # --- 3. BASELINE, HEURISTICS, RL AGENT (Middle Row) ---
    middle_y = split_y - 1.5
    
    # Baseline
    base_x = 3
    ax.add_patch(patches.Rectangle((base_x - w/2, middle_y - h/2), w, h, facecolor=COLOR_BASELINE, edgecolor=LINE_BASELINE, linewidth=2.5, alpha=1.0))
    plt.text(base_x, middle_y, 'Baseline', ha='center', va='center', fontsize=10, color='white', weight='bold')

    # Heuristics Pool
    heur_x = 7
    heur_w = 2.8
    ax.add_patch(patches.Rectangle((heur_x - heur_w/2, middle_y - h/2), heur_w, h, facecolor=COLOR_HEURISTICS, edgecolor=LINE_CORE, linewidth=2.5, alpha=1.0))
    plt.text(heur_x, middle_y, 'Heuristics Pool', ha='center', va='center', fontsize=10, color='white', weight='bold')
    
    # RL Agent
    rl_x = 11
    ax.add_patch(patches.Rectangle((rl_x - w/2, middle_y - h/2), w, h, facecolor=COLOR_RL_AGENT, edgecolor=LINE_RL, linewidth=2.5, alpha=1.0))
    plt.text(rl_x, middle_y, 'RL Agent', ha='center', va='center', fontsize=10, color='white', weight='bold')

    # Draw continuous bent lines from core engine
    ax.vlines(core_x, core_y - core_h/2, split_y, color=LINE_CORE, linewidth=2)
    
    # Left side: bent line to Baseline with arrow
    ax.hlines(split_y, core_x, base_x, color=LINE_CORE, linewidth=2)
    ax.annotate('', xy=(base_x, middle_y + h/2), xytext=(base_x, split_y),
                arrowprops=dict(arrowstyle="->", color=LINE_CORE, lw=2))
    
    # Right side: bent line to RL Agent with arrow
    ax.hlines(split_y, core_x, rl_x, color=LINE_CORE, linewidth=2)
    ax.annotate('', xy=(rl_x, middle_y + h/2), xytext=(rl_x, split_y),
                arrowprops=dict(arrowstyle="->", color=LINE_CORE, lw=2))

    # --- Connections to Heuristics (Using Your Labels) ---
    
    # Heuristics <-> Baseline
    plt.text(5.0, middle_y + 0.15, 'uses just one', ha='center', va='center', fontsize=9, color=LINE_BASELINE, style='italic', weight='bold')
    ax.annotate('', xy=(base_x + w/2, middle_y), xytext=(heur_x - heur_w/2, middle_y),
                arrowprops=dict(arrowstyle="<->", color=LINE_BASELINE, lw=2, ls='--'))
    
    # Heuristics <-> RL Agent
    plt.text(9.0, middle_y + 0.15, 'uses all at once', ha='center', va='center', fontsize=9, color=LINE_RL, style='italic', weight='bold')
    ax.annotate('', xy=(rl_x - w/2, middle_y), xytext=(heur_x + heur_w/2, middle_y),
                arrowprops=dict(arrowstyle="<->", color=LINE_RL, lw=2, ls='--'))

    # --- 4. LINUCB BANDIT (Learning/Control) ---
    bandit_x, bandit_y = 7, middle_y - h - 1.8
    bandit_w = 3.5
    ax.add_patch(patches.Rectangle((bandit_x - bandit_w/2, bandit_y - h/2), bandit_w, h, facecolor=COLOR_BANDIT, edgecolor=LINE_RL, linewidth=2.5, alpha=1.0))
    plt.text(bandit_x, bandit_y, 'RL Model (LinUCB)', ha='center', va='center', fontsize=10, color='white', weight='bold')
    
    # RL Agent -> Bandit (Online Learning)
    plt.text(9.7, middle_y - 1.5, 'Online Learning\nfor Heuristic\nSelection', ha='center', va='center', fontsize=8.5, color='white', weight='bold',
             bbox=dict(boxstyle='round,pad=0.4', facecolor=LINE_RL, edgecolor='none', alpha=0.9))
    ax.annotate('', xy=(bandit_x + bandit_w/2, bandit_y), xytext=(rl_x, middle_y - h/2),
                arrowprops=dict(arrowstyle="<->", connectionstyle="arc3,rad=-0.3", color=LINE_RL, lw=2))

    # Bandit <-> Heuristics (Selects Arm/Context)
    plt.text(heur_x - 0.5, (middle_y - h/2 + bandit_y + h/2) / 2, 'Selects\nHeuristics\nBased on\nSolver\nState', 
             ha='center', va='center', fontsize=8.5, color='white', weight='bold', rotation=90,
             bbox=dict(boxstyle='round,pad=0.3', facecolor=LINE_RL, edgecolor='none', alpha=0.9))
    ax.annotate('', xy=(heur_x, middle_y - h/2), xytext=(bandit_x, bandit_y + h/2),
                arrowprops=dict(arrowstyle="<->", color=LINE_RL, lw=2))

    # --- 5. END RESULT (Bottom) ---
    result_x, result_y = 7, bandit_y - h - 1.5
    result_w = 3.5  # Wider box for longer text
    ax.add_patch(patches.Rectangle((result_x - result_w/2, result_y - h/2), result_w, h, facecolor=COLOR_RESULT, edgecolor=LINE_CORE, linewidth=2.5, alpha=1.0))
    plt.text(result_x, result_y, 'End Result (Satisfiability)', ha='center', va='center', fontsize=11, color='white', weight='bold')

    # Connect Baseline to Result
    ax.annotate('', xy=(result_x - result_w/2, result_y), xytext=(base_x, middle_y - h/2),
                arrowprops=dict(arrowstyle="->", connectionstyle="angle,angleA=90,angleB=180", color=LINE_CORE, lw=2))
    
    # Connect RL Agent to Result
    ax.annotate('', xy=(result_x + result_w/2, result_y), xytext=(rl_x, middle_y - h/2),
                arrowprops=dict(arrowstyle="->", connectionstyle="angle,angleA=-90,angleB=0", color=LINE_CORE, lw=2))

    # Final Title
    plt.title('Context-Aware Heuristic Selection in CDCL SAT Solvers Using Online Reinforcement Learning', fontsize=14, weight='bold', pad=10)
    plt.savefig('solver_architecture_flowchart_sleek_final.png', dpi=300, bbox_inches='tight')
    plt.close(fig)

# Execute the function
generate_sleek_solver_architecture_flowchart()