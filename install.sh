#!/usr/bin/bash
# This script installs and configures museum_book_prototype on the current user's account.
set -e

PROJECT_NAME="museum_book_prototype"

USER_HOME=$(eval echo "~$USERNAME")
DEST_DIR="$USER_HOME/.local/share/$PROJECT_NAME"

# check if curl exists
if ! command -v curl &>/dev/null; then
  echo "curl is required but not installed. Please install curl and rerun the script."
  exit 1
fi

# install uv if not present
if ! command -v uv &>/dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "Installing $PROJECT_NAME to $DEST_DIR"

# copy project files
mkdir -p "$DEST_DIR"
cp -r ./* "$DEST_DIR"

# set ownership
chown -R "$USERNAME:$USERNAME" "$DEST_DIR"

# sync depedencies
echo "Syncing dependencies..."
"$USER_HOME/.local/bin/uv" --project="$DEST_DIR" sync

# create desktop/autostart entry

echo "Creating desktop and autostart entries..."

DESKTOP_DIR="$USER_HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
DESKTOP_FILE="$DESKTOP_DIR/$PROJECT_NAME.desktop"
cat >"$DESKTOP_FILE" <<EOL
[Desktop Entry]
Type=Application
Name=$PROJECT_NAME
Exec=bash -c 'cd $DEST_DIR && "$USER_HOME/.local/bin/uv" --project="$DEST_DIR" run "$DEST_DIR/src/$PROJECT_NAME/__main__.py"'
Terminal=false
EOL

AUTOSTART_DIR="$USER_HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

AUTOSTART_FILE="$AUTOSTART_DIR/$PROJECT_NAME.desktop"
cat >"$AUTOSTART_FILE" <<EOL
[Desktop Entry]
Type=Application
Name=$PROJECT_NAME
Exec=bash -c 'cd $DEST_DIR && "$USER_HOME/.local/bin/uv" --project="$DEST_DIR" run "$DEST_DIR/src/$PROJECT_NAME/__main__.py"'
Terminal=false
X-GNOME-Autostart-enabled=true
EOL

echo "Adding udev rule for USB permissions..."
UDEV_RULES_DIR="/etc/udev/rules.d"
UDEV_RULE_FILE="$UDEV_RULES_DIR/99-$PROJECT_NAME.rules"

sudo bash -c "cat >$UDEV_RULE_FILE" <<EOL
ACTION!="remove", SUBSYSTEMS=="usb-serial", TAG+="uaccess"
EOL

echo "Done!"
