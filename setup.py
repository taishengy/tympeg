from setuptools import setup, find_packages
setup(
    name="tympeg",
    version="0.2",
    packages=find_packages(),
    scripts=[],

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=['docutils>=0.3'],

    # package_data={
    #     # If any package contains *.txt or *.rst files, include them:
    #     '': ['*.txt', '*.rst'],
    #     # And include any *.msg files found in the 'hello' package, too:
    #     'hello': ['*.msg'],
    # },

    # metadata for upload to PyPI
    author="TaiSheng Yeager",
    author_email="taishengyeager@gmail.com",
    description="This package makes common ffmpeg functions easier such as:"
                "\tConverting files to new encodings"
                "\tClipping sections of files"
                "\tConcatanating files"
                "\tMetadata analysis"
                "\tSaving HLS streams",
    license="MIT",
    keywords="ffmpeg video audio subtitle HLS stream",
    url="https://github.com/taishengy/tympeg",   # project home page, if any

    # could also include long_description, download_url, classifiers, etc.
)
