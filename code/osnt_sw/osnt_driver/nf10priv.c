/*******************************************************************************
 *
 *  NetFPGA-10G http://www.netfpga.org
 *
 *  File:
 *        nf10priv.c
 *
 *  Project:
 *        nic
 *
 *  Author:
 *        Yilong Geng
 *        Mario Flajslik
 *
 *  Description:
 *        These functions control the card tx/rx operation. 
 *        nf10priv_xmit -- gets called for every transmitted packet
 *                         (on any nf interface)
 *        work_handler  -- gets called when the interrupt handler puts work
 *                         on the queue
 *        nf10priv_send_rx_dsc -- allocates and sends a receive descriptor
 *                                to the nic
 *
 *        There also exists a LOOPBACK_MODE (enabled by defining constant
 *        LOOPBACK_MODE) that allows the driver to be tested on a single
 *        machine. This mode, at receive, flips the last bit in the second
 *        to last octet of the source and destination IP addresses. (e.g.
 *        address 192.168.2.1 is converted to 192.168.3.1 and vice versa).
 *
 *        An example configuration that has been tested with loopback between 
 *        interfaces 0 and 3 (must add static ARP entries, because ARPs
 *        aren't fixed by the LOOPBACK_MODE):
 *            ifconfig nf0 192.168.2.11;
 *            ifconfig nf3 192.168.3.12;
 *            arp -s 192.168.2.12 00:4E:46:31:30:03;
 *            arp -s 192.168.3.11 00:4E:46:31:30:00;
 *
 *            "ping 192.168.2.12" -- should now work with packets going over
 *                                   the wire.
 *
 *
 *  Copyright notice:
 *        Copyright (C) 2010, 2011 The Board of Trustees of The Leland Stanford
 *                                 Junior University
 *
 *  Licence:
 *        This file is part of the NetFPGA 10G development base package.
 *
 *        This file is free code: you can redistribute it and/or modify it under
 *        the terms of the GNU Lesser General Public License version 2.1 as
 *        published by the Free Software Foundation.
 *
 *        This package is distributed in the hope that it will be useful, but
 *        WITHOUT ANY WARRANTY; without even the implied warranty of
 *        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *        Lesser General Public License for more details.
 *
 *        You should have received a copy of the GNU Lesser General Public
 *        License along with the NetFPGA source package.  If not, see
 *        http://www.gnu.org/licenses/.
 *
 */

#include "nf10priv.h"
#include <linux/spinlock.h>
#include <linux/pci.h>

#include <linux/netdevice.h>
#include <linux/etherdevice.h>
#include <linux/if_ether.h>
#include <net/ip.h>
#include <net/tcp.h>

#define SK_BUFF_ALLOC_SIZE  1533

//#define LOOPBACK_MODE

static DEFINE_SPINLOCK(tx_lock);
static DEFINE_SPINLOCK(work_lock);

DECLARE_WORK(wq, work_handler);

int nf10priv_xmit(struct nf10_card *card, struct sk_buff *skb, int port){
    uint8_t* data = skb->data;
    uint32_t len = skb->len;
    unsigned long flags;
    uint64_t pkt_addr = 0, pkt_addr_fixed = 0;
    uint64_t dsc_addr = 0, dsc_index = 0;
    uint64_t cl_size = (len + 2*63) / 64; // need engouh room for data in any alignment case
    uint64_t port_decoded = 0;
    uint64_t dsc_l0, dsc_l1;
    uint64_t dma_addr;

    if(len > 1514)
        printk(KERN_ERR "nf10: ERROR too big packet. TX size: %d\n", len);

    // packet buffer management
    spin_lock_irqsave(&tx_lock, flags);

    // make sure we fit in the descriptor ring and packet buffer
    if( (atomic64_read(&card->mem_tx_dsc.cnt) + 1 <= card->mem_tx_dsc.cl_size) &&
        (atomic64_read(&card->mem_tx_pkt.cnt) + cl_size <= card->mem_tx_pkt.cl_size)){
        
        pkt_addr = card->mem_tx_pkt.wr_ptr;
        card->mem_tx_pkt.wr_ptr = (pkt_addr + 64*cl_size) & card->mem_tx_pkt.mask;

        dsc_addr = card->mem_tx_dsc.wr_ptr;
        card->mem_tx_dsc.wr_ptr = (dsc_addr + 64) & card->mem_tx_dsc.mask;

        // get physical address of the data
        dma_addr = pci_map_single(card->pdev, data, len, PCI_DMA_TODEVICE);
        
        if(pci_dma_mapping_error(card->pdev, dma_addr)){
            printk(KERN_ERR "nf10: dma mapping error");
            spin_unlock_irqrestore(&tx_lock, flags);
            return -1;
        }

        atomic64_inc(&card->mem_tx_dsc.cnt);
        atomic64_add(cl_size, &card->mem_tx_pkt.cnt);
        
        // there is space in the descriptor ring and at least 2k space in the pkt buffer
        if( !(( atomic64_read(&card->mem_tx_dsc.cnt) + 1 <= card->mem_tx_dsc.cl_size  ) &&
              ( atomic64_read(&card->mem_tx_pkt.cnt) + 32 <= card->mem_tx_pkt.cl_size )) ){   

            netif_stop_queue(card->ndev[port]);
        }

    } 
    else{
        spin_unlock_irqrestore(&tx_lock, flags);
        return -1;
    }
    
    spin_unlock_irqrestore(&tx_lock, flags);

    dsc_index = dsc_addr / 64;
    
    // figure out ports
    if(port == 0)
        port_decoded = 0x0102;
    else if(port == 1)
        port_decoded = 0x0408;
    else if(port == 2)
        port_decoded = 0x1020;
    else if(port == 3)
        port_decoded = 0x4080;

    // fix address for alignment issues
    pkt_addr_fixed = pkt_addr + (dma_addr & 0x3fULL);

    // prepare TX descriptor
    dsc_l0 = ((uint64_t)len << 48) + ((uint64_t)port_decoded << 32) + (pkt_addr_fixed & 0xffffffff);
    dsc_l1 = dma_addr;

    // book keeping
    card->tx_bk_dma_addr[dsc_index] = dma_addr;
    card->tx_bk_skb[dsc_index] = skb;
    card->tx_bk_size[dsc_index] = cl_size;
    card->tx_bk_port[dsc_index] = port;

    // write to the card
    mb();
    *(((uint64_t*)card->tx_dsc) + 8 * dsc_index + 0) = dsc_l0;
    *(((uint64_t*)card->tx_dsc) + 8 * dsc_index + 1) = dsc_l1;
    mb();

    return 0;
}

void work_handler(struct work_struct *w){
    struct nf10_card * card = ((struct my_work_t *)w)->card;
    int irq_done = 0;
    uint32_t tx_int;
    uint64_t rx_int;
    uint64_t timestamp;
    uint64_t addr;
    uint64_t index;
    uint64_t len;
    int port = -1;
    uint64_t port_encoded;
    unsigned long flags;
#ifdef LOOPBACK_MODE
    struct iphdr *iph;
    struct tcphdr *th;
    struct sock sck;
    struct inet_sock *isck;
#endif
    int work_counter = 0;
    int tcnt = 1;
    int int_enabled = 1;
    int i;

    spin_lock_irqsave(&work_lock, flags);

    while(tcnt){

        if((int_enabled == 1) && work_counter > 0){
            int_enabled = 0;
            mb();
            *(((uint64_t*)card->cfg_addr)+25) = 0; // disable TX interrupts
            mb();
        }

        irq_done = 1;
        
        // read the host completion buffers
        tx_int = *(((uint32_t*)card->host_tx_dne_ptr) + (card->host_tx_dne.rd_ptr)/4);

        if( (tx_int & 0xffff) == 1 ){
            irq_done = 0;
            
            // manage host completion buffer
            addr = card->host_tx_dne.rd_ptr;
            card->host_tx_dne.rd_ptr = (addr + 64) & card->host_tx_dne.mask;
            index = addr / 64;
            
            // clean up the skb
            pci_unmap_single(card->pdev, card->tx_bk_dma_addr[index], card->tx_bk_skb[index]->len, PCI_DMA_TODEVICE);
            dev_kfree_skb_any(card->tx_bk_skb[index]);
            atomic64_sub(card->tx_bk_size[index], &card->mem_tx_pkt.cnt);
            atomic64_dec(&card->mem_tx_dsc.cnt);
            
            // invalidate host tx completion buffer
            *(((uint32_t*)card->host_tx_dne_ptr) + index * 16) = 0xffffffff;

            // restart queue if needed
            if( ((atomic64_read(&card->mem_tx_dsc.cnt) + 8*1) <= card->mem_tx_dsc.cl_size) &&
                ((atomic64_read(&card->mem_tx_pkt.cnt) + 4*32) <= card->mem_tx_pkt.cl_size) ){
                
                for(i = 0; i < 4; i++){
                    if(netif_queue_stopped(card->ndev[i]))
                        netif_wake_queue(card->ndev[i]);
                }

            }
        }

        work_counter++;

        if(irq_done)
            tcnt--;
        else if(tcnt < 10000)
            tcnt++;

        if((tcnt <= 1) && (int_enabled == 0)){
            work_counter = 0;
            tcnt = 1;
            int_enabled = 1;
            mb();
            *(((uint64_t*)card->cfg_addr)+25) = 1; // enable TX interrupts
            mb();
        }
    }

    spin_unlock_irqrestore(&work_lock, flags);
}
