# About this project
This project is a website for a Discord server, built with Python and the Flask framework. It acts as an interface between the Discord bot, the website, and related services, centralizing management and community interaction while simplifying the integration of new features.
# Features
- **User Authentication**: Secure login and registration system thanks to OIDC.
- **Discord Integration**: Seamless connection with Discord for real-time updates and interactions.
- **Admin Dashboard**: Manage server settings, user roles, and permissions.
- **Community Engagement**: Forums, announcements, and event management. (I need to have a reflection on this)
- **Responsive Design**: Optimized for both desktop and mobile devices.

# Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/drtabkebasse/SaucisseLand-WebSite.git
    ```
2. Navigate to the project directory:
    ```bash
    cd SaucisseLand-WebSite
    ```
3. Create a virtual environment:
    ```bash
    python -m venv venv
    ```
4. Activate the virtual environment:

    - On Windows:
      ```bash
      venv\Scripts\activate
      ```
    - On macOS/Linux:
      ```bash
      source venv/bin/activate
      ```

5. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
6. Set up the environment variables:
    ```bash
    cp .env.example .env
    ```
7. Run the application:
    ```bash
    flask run
    ```

# Contributing
Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Clone your fork locally and navigate to the project directory.
3. **Create a Python virtual environment** to isolate dependencies:
    ```bash
    python -m venv venv
    ```
    - Activate the virtual environment:
      - On Windows:
         ```bash
         venv\Scripts\activate
         ```
      - On macOS/Linux:
         ```bash
         source venv/bin/activate
         ```
4. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5. Create a new branch:
    ```bash
    git checkout -b feature/your-feature-name
    ```
6. Make your changes and commit them:
    ```bash
    git commit -m "Add your commit message"
    ```
7. Push the changes to your fork:
    ```bash
    git push origin feature/your-feature-name
    ```
8. Create a pull request on the original repository.

# License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.