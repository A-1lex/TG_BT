{ pkgs }: {
  deps = [
    pkgs.ffmpeg
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.setuptools
    pkgs.python311Packages.wheel
    pkgs.python311Packages.aiogram
    pkgs.python311Packages.python-dotenv
    pkgs.python311Packages.requests
  ];
}
