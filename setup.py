from setuptools import setup, find_packages, SetuptoolsDeprecationWarning
import warnings

warnings.filterwarnings("ignore", category=SetuptoolsDeprecationWarning)

package_name = 'pigpiod_emulator'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude="tools"),
    install_requires=['setuptools>=68.2.2'],
    maintainer='7Robot',
    maintainer_email='7robot@bde.enseeiht.fr',
    description='TODO: Package description',
    license='TODO: License declaration',
)
