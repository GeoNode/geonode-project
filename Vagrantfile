# Vagrant 1.7+ automatically inserts a different
# insecure keypair for each new VM created. The easiest way
# to use the same keypair for all the machines is to disable
# this feature and rely on the legacy insecure key.
# config.ssh.insert_key = false
#
# Note:
# As of Vagrant 1.7.3, it is no longer necessary to disable
# the keypair creation when using the auto-generated inventory.
$geonode_source_path=/home/luca/Development/geonode-project
$script1 = <<-'SCRIPT'
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get -y install docker-ce docker-ce-cli containerd.io
sudo adduser vagrant docker
sudo docker swarm init
SCRIPT

$script2 = <<-'SCRIPT'
if [ -d "$HOME/antani" ]; then
    cd $HOME/antani
    [ -f $HOME/antani/.env ] && docker-compose down
    cd ..
    sudo rm -rf $HOME/antani
fi    
SCRIPT

$script3 = <<-'SCRIPT'
sudo apt-get update
sudo apt-get -y install python3-pip python3-virtualenv virtualenvwrapper
SCRIPT

Vagrant.configure(2) do |config|
    boxes = {
            'ubuntu01' => 'ubuntu/focal64'
    }
    machine_id = 0
    boxes.each do | key, value |
        config.vm.box = "#{value}"
        machine_id = machine_id + 1
        
        
        config.vm.define "#{key}" do |node|
            node.vm.hostname = "#{key}"
            #node.vm.network "private_network", ip: "192.168.68.#{20+machine_id}"    
            # Only execute once the Ansible provisioner,
            # when all the machines are up and ready.
        
        config.vm.provision "shell", inline: $script1, privileged: false
        config.vm.provision "shell", inline: $script2, run: 'always', privileged: false
        #edit source path suiting your needs
        config.vm.provision "file", source: $geonode_source_path, destination: "$HOME/geonode-project", run: 'always'
        config.vm.provision "shell", inline: $script3, run: 'always', privileged: false
        config.vm.provision :shell, path: "antani-vagrant.sh", run: 'always', privileged: false
        

        end
    end
end