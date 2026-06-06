{ pkgs, agenix, agenixManagerModule, common }:
let
  hostKey = common.genKeyPair "host";
  hostPubText = builtins.readFile "${hostKey}/key.pub";
  encryptedSecret = common.encrypt "test-secret" [ hostKey ] "custom-perms-secret";
  manifestFile = pkgs.writeText "secrets-manifest.json" (builtins.toJSON {
    version = 1;
    secrets = [
      {
        name = "test-secret";
        scope = "systems";
        owner = "nobody";
        group = "nogroup";
        mode = "0440";
      }
    ];
  });
in {
  name = "custom-perms";

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
      manifestPath = "${manifestFile}";
      keys.groups.systems = [ hostPubText ];
      identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
    };

    system.stateVersion = config.system.nixos.release;
  };

  testScript = ''
    machine.wait_for_unit("multi-user.target")

    machine.succeed("test -f /etc/agenix/secrets.nix")

    decrypted = machine.succeed("cat /run/agenix/test-secret")
    assert decrypted.strip() == "custom-perms-secret", f"Unexpected content: {decrypted}"

    owner = machine.succeed("stat -c '%U:%G' /run/agenix/test-secret").strip()
    assert owner == "nobody:nogroup", f"Expected nobody:nogroup, got {owner}"

    perms = machine.succeed("stat -c '%a' /run/agenix/test-secret").strip()
    assert perms == "440", f"Expected 440 perms, got {perms}"
  '';
}
