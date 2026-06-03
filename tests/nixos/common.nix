{ pkgs }:

{
  genKeyPair = name: pkgs.runCommand "${name}-key" {
    nativeBuildInputs = [ pkgs.openssh ];
  } ''
    mkdir -p "$out"
    ssh-keygen -t ed25519 -f "$out/key" -N "" -q
  '';

  encrypt = name: keyDirs: plaintext: pkgs.runCommand "${name}.age" {
    nativeBuildInputs = [ pkgs.age ];
  } ''
    echo -n "${plaintext}" \
      | age ${builtins.concatStringsSep " " (map (d: "-R \"${d}/key.pub\"") keyDirs)} \
          -o "$out"
  '';
}
