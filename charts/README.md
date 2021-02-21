# Installation with `helm` on `microk8s` `Kubernetes`

The following examples assume Ubuntu 20.04.1, but should work fine on any recent Linux that `snap` is installed properly on.

Perform any system updates so you are starting from where you should be:

```
sudo apt update && sudo apt -y dist-upgrade && sudo apt -y autoremove
sudo reboot
```
Now install and configure `microk8s` with the required addons for `djankiserv`:
```
sudo snap install microk8s --channel=1.20 --classic
sudo microk8s.enable storage dns
sudo snap alias microk8s.kubectl kubectl
sudo snap install helm --classic
sudo usermod -a -G microk8s $USER
logout
```
You need to be in the correct group, so make sure you do logout/login, then continue setting up `cert-manager` for SSL certs:
```
mkdir -p ~/.kube/ && kubectl config view --raw >~/.kube/config
kubectl create namespace cert-manager
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm upgrade --install cert-manager jetstack/cert-manager --namespace cert-manager --version 1.2.0 --set installCRDs=true
```
Now get the helm chart (a chart repo will be set up soon):
```
git clone https://gitlab.com/melser.anton/djankiserv.git
```

!!! Now create a file with your overrides, you will need at least to put a domain name that points to your public IP, that points ports 80 and 443 to this machine

```
vi overrides.yaml
```
```
djankiserv:
  host: your.fqdn.tld

ingress:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging
  tls:
    secretName: letsencrypt-cert-staging

clusterissuer:
  staging:
    enabled: true
    email: certs@your.fqdn.tld
  # prod:
  #   enabled: false
  #   email: certs@your.fqdn.tld
```
You are now ready to install the chart:
```
helm install -f overrides.yaml whatever_name_you_like djankiserv/charts/djankiserv/
```
You can then get progress by executing:
```
kubectl get pods
```
When all pods report "Running" in the "STATUS" column and "1/1" in the "READY" column you should be good to get started.

You may also prefer to have a stable way to refer to your main pod, which you can do, for example, with the following alias in `.bashrc` or `.bash_aliases`:
```
alias pn.djs='kubectl get pod -l app.kubernetes.io/name=djankiserv -o jsonpath="{.items[0].metadata.name}"'
```
Now perform the migrations:
```
kubectl exec -it $(pn.djs) -- python manage.py migrate
```
And create a superuser
```
kubectl exec -it $(pn.djs) -- python manage.py createsuperuser
```

You should now go to your spanking new site and make sure it has been given a Let's Encrypt staging cert.

```
echo | openssl s_client -connect your.fqdn.tld:443 2>/dev/null | grep "issuer=C"
```
If you see the output:
```
issuer=CN = Fake LE Intermediate X1
```
Then you are all set to activate the proper, production certificate. If not (particularly if you see something related to Kubernetes), try making sure the `clusterissuer` has been created correctly:
```
kubectl describe clusterissuer letsencrypt-staging
```
Assuming you are good, you should now go and modify your `overrides.yaml` file to activate the production cert:
```
djankiserv:
  host: your.fqdn.tld

ingress:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  tls:
    secretName: letsencrypt-cert-prod

clusterissuer:
  staging:
    enabled: true
    email: certs-staging@your.favourite.email
  prod:
    enabled: false
    email: certs-prod@your.favourite.email
```
Upgrade your installation with the new values:
```
helm upgrade -f overrides.yaml whatever_name_you_like djankiserv/charts/djankiserv/
```
After a few minutes when you execute:
```
echo | openssl s_client -connect your.fqdn.tld:443 2>/dev/null | grep "issuer=C"
```
you should get:
```
issuer=C = US, O = Let's Encrypt, CN = Let's Encrypt Authority X3
```
Now when you go to `https://your.fqdn.tld/` you should not get any errors in your browser, and it should take you over to the admin page.
