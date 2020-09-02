import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="kang", # Replace with your own username
    version="0.0.1",
    author="Cedric Bosdonnat",
    author_email="cedric.bosdonnat@free.fr",
    description="An SMS-controlled heating system for raspberry pi and SIM800L",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cbosdo/kang",
    packages=["kang"],
    entry_points={
        "console_scripts": [
            "kang = kang.kang:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
