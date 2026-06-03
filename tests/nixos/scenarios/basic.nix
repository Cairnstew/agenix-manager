{ pkgs, agenix, agenixManagerModule, common }:
let
  hostKey = common.genKeyPair "host";
  hostPubText = builtins.readFile "${hostKey}/key.pub";
  encryptedSecret = common.encrypt "test-secret" [ hostKey ] "hello-from-agenix";
in {
  name = "basic";

  nodeConfig = { config, pkgs, ... }: {
    imports = [ agenix.nixosModules.default agenixManagerModule ];

    system.activationScripts.activatePlaceAgenixTestFiles = {
      text = ''
        mkdir -p /etc/secrets /etc/ssh
        cp ${hostKey}/key /etc/ssh/ssh_host_ed25519_key
        chmod 0600 /etc/ssh/ssh_host_ed25519_key
        cp ${encryptedSecret} /etc/secrets/test-secret.age
        chmod 0644 /etc/secrets/test-secret.age
      '';
      deps = [];
    };

    agenixManager = {
      enable = true;
      secretsPath = "/etc/secrets";
      flakeRoot = "/etc/nixos";
      keys.systems = [ hostPubText ];
      identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
      secrets = [
        { name = "test-secret"; keys = "systems"; }
      ];
    };

    system.stateVersion = config.system.nixos.release;
  };

  testScript = ''
    machine.wait_for_unit("multi-user.target")

    machine.succeed("test -f /etc/secrets/secrets.nix")
    content = machine.succeed("cat /etc/secrets/secrets.nix")
    assert "test-secret.age" in content, f"secrets.nix missing entry:\n{content}"

    decrypted = machine.succeed("cat /run/agenix/test-secret")
    assert decrypted.strip() == "hello-from-agenix", f"Unexpected content: {decrypted}"

    perms = machine.succeed("stat -c '%a' /run/agenix/test-secret").strip()
    assert perms == "400", f"Expected 400 perms, got {perms}"
  '';
}
