# Test Datasets and Commands

Test datasets, including reference genome and taxonomy databases, query sequencing data are based on a a collection of 107 NCBI-defined "reference" bacterial genomes. The database is available for download at:

## Align

*Sequence alignment** results.

Here "alignment" refers to the operation of aligning short DNA sequences ("reads") against reference **genome** sequences.

The query sequences are five samples (S01 to S05) of 150 bp paired-end reads simulated using [CAMISIM](https://github.com/CAMI-challenge/CAMISIM/). The ground-truth mapping of reads against original genomes and locations are provided in `truth`.

Four aligners were used: [BLASTn](https://blast.ncbi.nlm.nih.gov/Blast.cgi), [Bowtie2](http://bowtie-bio.sourceforge.net/bowtie2/index.shtml), [Centrifuge](https://ccb.jhu.edu/software/centrifuge/), and [BURST](https://github.com/knights-lab/BURST). In particular, `bowtie2` used the Bowtie2 program default, whereas `bt2sho` used the Bowtie2 parameter setting recommended by SHOGUN. The mappings between reads and genomes are provided by each alignment file.

In addition, `burst/split` is the mapping against **genes** annotated from the reference genomes (not genomes themselves).

## Taxonomy

**Reference taxonomy** of the 107 bacterial genomes. The taxonomy is provided in multiple formats:

- `g2tid.txt`: Genome ID to NCBI taxonomy ID mapping file.
- `taxdump`: NCBI taxdump-style database files (`nodes.dmp` and `names.dmp`).
- `lineage.txt`: Greengenes-style lineage strings.
- `rank_names.tsv` and `rank_tids.tsv`: Taxon name and TaxID at each of the seven standard taxonomic ranks for each genome.

In addition, `nucl/` contains the mappings from nucleotide sequence accessions (instead of their host genomes) to taxonomy.

## Phylogeny

- `tree.nwk`: Maximum likelihood phylogenetic tree of the 107 bacterial genomes built using [RAxML](https://cme.h-its.org/exelixis/web/software/raxml/index.html) and midpoint-rooted.

## Function

**Functional annotations** of genes ([Prodigal](https://github.com/hyattpd/Prodigal)-predicted ORFs) on the 107 genomes.

- `coords.txt`: Coordinates of genes on their host genomes
- `uniref.map`: Mapping of genes to [UniRef](https://www.uniprot.org/help/uniref) entries.
- `go/`: Mapping of UniRef entries to [GO](http://geneontology.org/docs/ontology-documentation/) terms.
- `nucl/`: See above.

## Output

Woltka output files generated from the provided alignments and classification systems. The commands for generating those files are:

`bowtie2.gotu.tsv`:

```bash
woltka gotu -i align/bowtie2 -o bowtie2.gotu.tsv
```

`bowtie2.free.tsv`:

```bash
woltka classify \
  --input align/bowtie2 \
  --map taxonomy/g2tid.txt \
  --nodes taxonomy/nodes.dmp \
  --rank free \
  --output bowtie2.free.tsv
```

`blastn.species.tsv`:

```bash
woltka classify \
  --input align/blastn/mux.b6o.xz \
  --lineage taxonomy/lineage.txt \
  --rank species \
  --output blastn.species.tsv
```

`blastn.species.biom`: Same as above, replacing `.tsv` with `.biom`.

`burst.genus.tsv`:

```bash
woltka classify \
  --input align/burst \
  --map taxonomy/g2tid.txt \
  --nodes taxonomy/nodes.dmp \
  --names taxonomy/names.dmp \
  --rank genus \
  --name-as-id \
  --output burst.genus.tsv
```

`burst.genus.map/`: Same as above, adding:

```bash
--outmap burst.genus.map
```

`bt2sho.phylo.tsv`

```bash
woltka classify \
  --input align/bt2sho \
  --newick tree.nwk \
  --rank free \
  --name-as-id \
  --output bt2sho.phylo.tsv
```

`burst.process.tsv`:

```bash
woltka classify \
  --input align/burst \
  --coords function/coords.txt.xz \
  --map function/uniref.map.xz \
  --map function/go/process.tsv.xz \
  --map-as-rank \
  --rank process \
  --output burst.process.tsv
```

`burst.genus.process.tsv`: Same as above, adding:

```bash
--stratify burst.genus.map
```

`split.genus.tsv`:

```bash
woltka classify \
  --input align/burst/split \
  --trim-sub _ \
  --map taxonomy/nucl/nucl2tid.txt \
  --nodes taxonomy/nodes.dmp \
  --names taxonomy/names.dmp \
  --rank genus \
  --name-as-id \
  --output split.genus.tsv
```

`split.process.tsv`:

```bash
woltka classify \
  --input align/burst/split \
  --map function/nucl/uniref.map.xz \
  --map function/go/process.tsv.xz \
  --map-as-rank \
  --rank process \
  --output split.process.tsv
```
