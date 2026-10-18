"""Light theme for Templar applications."""

import sys
sys.dont_write_bytecode = True


def render():
    """Return light theme CSS."""
    return '''
    :root {
        --primary-color: #007bff;
        --secondary-color: #6c757d;
        --success-color: #28a745;
        --danger-color: #dc3545;
        --warning-color: #ffc107;
        --info-color: #17a2b8;
        
        --bg-color: #ffffff;
        --text-color: #333333;
        --border-color: #dee2e6;
        --shadow-color: rgba(0, 0, 0, 0.1);
    }
    
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        line-height: 1.6;
        color: var(--text-color);
        background-color: var(--bg-color);
    }
    
    h1, h2, h3, h4, h5, h6 {
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    p {
        margin-bottom: 1rem;
    }
    
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 20px;
    }
    
    .navbar {
        background-color: var(--primary-color);
        color: white;
        padding: 1rem 0;
        box-shadow: 0 2px 4px var(--shadow-color);
    }
    
    .navbar-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .brand {
        font-size: 1.5rem;
        font-weight: bold;
        color: white !important;
        text-decoration: none;
    }
    
    .nav-links {
        display: flex;
        gap: 2rem;
        list-style: none;
    }
    
    .nav-links a {
        color: white;
        text-decoration: none;
        transition: opacity 0.3s;
    }
    
    .nav-links a:hover {
        opacity: 0.8;
    }
    
    .main-content {
        padding: 2rem 0;
        min-height: 60vh;
    }
    
    .footer {
        background-color: #f8f9fa;
        border-top: 1px solid var(--border-color);
        padding: 2rem 0;
        text-align: center;
        color: var(--text-color);
    }
    
    .cards-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 2rem;
        margin: 2rem 0;
    }
    
    .button-group {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }
    
    .centered {
        text-align: center;
    }
    '''


def get_styles():
    return render()
